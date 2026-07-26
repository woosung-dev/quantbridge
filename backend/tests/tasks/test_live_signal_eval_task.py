"""Sprint 26 — `live_signal.evaluate_all` (eval task) 단위 테스트.

검증 범위:
- Beat schedule 등록 (`evaluate-live-signals`, 60s schedule, expires=50)
- task name `live_signal.evaluate_all` 등록
- RedisLock contention → skipped="contention" + qb_live_signal_skipped_total inc
- last_bar_time CAS — 같은 bar 두 번 fire 시 두 번째 claim_lost
- non-Demo account → skipped="non_demo_account"
- StrategySettings malformed → skipped="invalid_settings"
- session_inactive → skipped="session_inactive"
- 정상 success → run_live + outbox INSERT + dispatch enqueue + outcome="success"
- claim_winner_only — 2 concurrent (asyncio.gather) → 1건 only inserts events

Sprint 18 BL-080 prefork-safe — `create_worker_engine_and_sm` 를 monkeypatch 로
in-memory mock 주입. `_async_evaluate_session` / `_evaluate_session_inner` 직접
await (run_in_worker_loop 우회 — 이미 pytest-asyncio loop 안에서 실행).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# ⚠️ src/tasks/__init__.py 가 `from src.tasks.celery_app import celery_app` 로 재export
# 하여 `import src.tasks.celery_app as X` 가 Celery 인스턴스로 평가됨. sys.modules 우회.
import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]

from src.common.metrics import (  # noqa: E402
    qb_live_signal_divergence_total,
    qb_live_signal_evaluated_total,
    qb_live_signal_skipped_total,
)
from src.strategy.pine_v2.event_loop import LiveSignal, LiveSignalResult  # noqa: E402
from src.trading.models import (  # noqa: E402
    AlertChannel,
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    LiveSignalInterval,
)

_STOP_ENTRY_SOURCE = (
    Path(__file__).parents[1] / "fixtures" / "pine_corpus_v2" / "s1_pbr.pine"
).read_text()
_MARKET_ENTRY_SOURCE = (
    Path(__file__).parents[3] / "frontend" / "public" / "samples" / "ema-crossover.pine"
).read_text()


async def _flush_pending_alerts() -> None:
    """fire-and-forget alert task(create_task) 가 완료되도록 yield (kill_switch test 패턴)."""
    for _ in range(5):
        await asyncio.sleep(0.01)


def _divergence_count(stage: str, category: str) -> float:
    """BL-362 — 특정 (stage, category) divergence counter 의 현재 값."""
    return qb_live_signal_divergence_total.labels(stage=stage, category=category)._value.get()


def _divergence_total() -> float:
    """모든 divergence label series의 합계다."""
    return sum(
        sample.value
        for metric in qb_live_signal_divergence_total.collect()
        for sample in metric.samples
        if sample.name == "qb_live_signal_divergence_total"
    )


# ── Beat schedule + task registration ──────────────────────────────────


def test_evaluate_task_registered_in_celery() -> None:
    assert "live_signal.evaluate_all" in celery_module.celery_app.tasks


def test_dispatch_task_registered_in_celery() -> None:
    assert "live_signal.dispatch_event" in celery_module.celery_app.tasks


def test_dispatch_pending_task_registered_in_celery() -> None:
    """codex G.2 P1 #10 fix — outbox 회수 Beat task 등록 검증."""
    assert "live_signal.dispatch_pending" in celery_module.celery_app.tasks


def test_dispatch_pending_beat_schedule_entry() -> None:
    """codex G.2 P1 #10 — 5분 Beat schedule 등록."""
    schedule = celery_module.celery_app.conf.beat_schedule
    assert "dispatch-pending-live-signal-events" in schedule
    entry = schedule["dispatch-pending-live-signal-events"]
    assert entry["task"] == "live_signal.dispatch_pending"
    assert entry["schedule"] == 300.0
    assert entry["options"]["expires"] == 240


def test_evaluate_beat_schedule_entry() -> None:
    schedule = celery_module.celery_app.conf.beat_schedule
    assert "evaluate-live-signals" in schedule
    entry = schedule["evaluate-live-signals"]
    assert entry["task"] == "live_signal.evaluate_all"
    assert entry["schedule"] == 60.0
    assert entry["options"]["expires"] == 50


# ── Helper: MockSessionContext ──────────────────────────────────────────


class _FakeAsyncContextLock:
    """RedisLock 대체 — __aenter__ 반환값을 fixture 가 제어."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.acquired_value = True
        self.extend_calls: list[int] = []

    async def __aenter__(self) -> bool:
        return self.acquired_value

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def extend(self, ttl_ms: int) -> bool:
        self.extend_calls.append(ttl_ms)
        return True


def _make_engine_sm_mocks(session_mock: AsyncMock) -> tuple[Any, Any]:
    """create_worker_engine_and_sm 대체용 (engine, sessionmaker) 튜플."""
    engine = AsyncMock()
    engine.dispose = AsyncMock()

    class _SMContext:
        async def __aenter__(self) -> AsyncMock:
            return session_mock

        async def __aexit__(self, *_exc: object) -> None:
            return None

    def _sm_factory() -> _SMContext:
        return _SMContext()

    return engine, _sm_factory


# ── _async_evaluate_session — RedisLock contention ────────────────────


@pytest.mark.asyncio
async def test_redislock_contention_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """RedisLock acquired=False → skipped='contention' + 즉시 반환."""
    fake_lock = _FakeAsyncContextLock()
    fake_lock.acquired_value = False

    def _factory(*_a: object, **_kw: object) -> _FakeAsyncContextLock:
        return fake_lock

    monkeypatch.setattr(live_signal_module, "RedisLock", _factory)

    res = await live_signal_module._async_evaluate_session(uuid4(), "1m")
    assert res == {"skipped": "contention"}


# ── _evaluate_session_inner — branch tests ─────────────────────────────


def _build_session_obj(
    *,
    is_active: bool = True,
    last_evaluated_bar_time: datetime | None = None,
    equity_baseline_usdt: Decimal | None = Decimal("8192.00"),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=is_active,
        last_evaluated_bar_time=last_evaluated_bar_time,
        equity_baseline_usdt=equity_baseline_usdt,
    )


def _patch_inner_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sess_repo: AsyncMock,
    event_repo: AsyncMock,
    account_repo: AsyncMock,
    strategy_repo: AsyncMock,
    ohlcv_rows: list[list[Any]] | None = None,
    run_live_result: LiveSignalResult | None = None,
    carry_result: tuple[Decimal, int] = (Decimal("0"), 0),
    ledger_result: tuple[Decimal, int] | None = None,
) -> AsyncMock:
    """공통 의존성 patching. session mock 반환."""
    session = AsyncMock()
    session.rollback = AsyncMock()
    engine, sm_factory = _make_engine_sm_mocks(session)

    def _engine_factory() -> tuple[Any, Any]:
        return engine, sm_factory

    monkeypatch.setattr(live_signal_module, "create_worker_engine_and_sm", _engine_factory)

    def _repo_class_factory(repo_mock: AsyncMock) -> Any:
        return MagicMock(return_value=repo_mock)

    # repository import 위치는 _evaluate_session_inner 함수 내부 (lazy).
    # 따라서 import 된 module 의 attribute 를 patch.
    import src.strategy.repository as strategy_repo_mod
    import src.trading.repositories.exchange_account_repository as account_repo_mod
    import src.trading.repositories.live_signal_event_repository as event_repo_mod
    import src.trading.repositories.live_signal_session_repository as sess_repo_mod

    monkeypatch.setattr(
        sess_repo_mod, "LiveSignalSessionRepository", _repo_class_factory(sess_repo)
    )
    monkeypatch.setattr(
        event_repo_mod, "LiveSignalEventRepository", _repo_class_factory(event_repo)
    )
    monkeypatch.setattr(
        account_repo_mod, "ExchangeAccountRepository", _repo_class_factory(account_repo)
    )
    monkeypatch.setattr(strategy_repo_mod, "StrategyRepository", _repo_class_factory(strategy_repo))

    # CCXT provider — fetch_ohlcv 결과 주입
    fake_provider = AsyncMock()
    fake_provider.fetch_ohlcv = AsyncMock(return_value=ohlcv_rows or [])
    monkeypatch.setattr(celery_module, "get_ccxt_provider_for_worker", lambda: fake_provider)

    # run_live → 정해진 결과 또는 빈 signals
    if run_live_result is None:
        run_live_result = LiveSignalResult(
            last_bar_time=datetime(2026, 5, 1, tzinfo=UTC),
            signals=[],
            strategy_state_report={"open_trades": {}},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
        )
    import src.strategy.pine_v2.event_loop as event_loop_mod

    monkeypatch.setattr(event_loop_mod, "run_live", lambda *a, **kw: run_live_result)
    event_repo.sum_realized_pnl_before = AsyncMock(return_value=carry_result)
    event_repo.sum_realized_pnl_all = AsyncMock(
        return_value=ledger_result if ledger_result is not None else carry_result
    )

    return session


@pytest.mark.asyncio
async def test_session_inactive_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=_build_session_obj(is_active=False))
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=AsyncMock(),
        strategy_repo=AsyncMock(),
    )
    res = await live_signal_module._evaluate_session_inner(uuid4(), "1m")
    assert res == {"skipped": "session_inactive"}


@pytest.mark.asyncio
async def test_invalid_settings_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """strategy.settings malformed → skipped='invalid_settings'."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": "not-a-number"},  # malformed
            pine_source="//@version=5\nstrategy('x')",
        )
    )

    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=AsyncMock(),
        strategy_repo=strategy_repo,
    )
    res = await live_signal_module._evaluate_session_inner(uuid4(), "1m")
    assert res["skipped"] == "invalid_settings"


@pytest.mark.asyncio
async def test_non_demo_account_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """account.mode=live → skipped='non_demo_account'."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 2, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
        )
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.live)
    )

    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=account_repo,
        strategy_repo=strategy_repo,
    )
    res = await live_signal_module._evaluate_session_inner(uuid4(), "1m")
    assert res == {"skipped": "non_demo_account"}


@pytest.mark.asyncio
async def test_no_new_bar_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """last_bar_time <= last_evaluated_bar_time → skipped='no_new_bar'."""
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess = _build_session_obj(last_evaluated_bar_time=bar_time)
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 2, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
        )
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )

    # 같은 bar_time 의 OHLCV
    bar_ms = int(bar_time.timestamp() * 1000)
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        ohlcv_rows=[[bar_ms, 1, 2, 0, 1, 100]],
    )
    res = await live_signal_module._evaluate_session_inner(uuid4(), "1m")
    assert res == {"skipped": "no_new_bar"}


@pytest.mark.asyncio
async def test_claim_lost_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """try_claim_bar=False → session.rollback() + skipped='claim_lost'."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=False)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 2, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
        )
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )

    bar_ms = int(datetime(2026, 5, 1, 12, 0, tzinfo=UTC).timestamp() * 1000)
    session = _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        ohlcv_rows=[[bar_ms, 1, 2, 0, 1, 100]],
    )
    res = await live_signal_module._evaluate_session_inner(uuid4(), "1m")
    assert res == {"skipped": "claim_lost"}
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_success_inserts_events_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 흐름 — claim won → run_live → outbox INSERT + state upsert + commit (LESSON-019).

    `dispatch_live_signal_event_task.apply_async` 가 신규 event 1건당 1회 호출.
    """
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.upsert_state = AsyncMock()
    sess_repo.commit = AsyncMock()

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 2, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
            trading_sessions=[],
        )
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )
    new_event_id = uuid4()
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    inserted_event = SimpleNamespace(
        id=new_event_id,
        bar_time=bar_time,
        sequence_no=0,
        action="entry",
        trade_id="L",
        status=LiveSignalEventStatus.pending,
    )
    event_repo = AsyncMock()
    event_repo.list_by_session = AsyncMock(return_value=[])  # 기존 events 없음
    event_repo.insert_pending_events = AsyncMock(return_value=[inserted_event])

    bar_ms = int(bar_time.timestamp() * 1000)
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=event_repo,
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        ohlcv_rows=[[bar_ms, 1, 2, 0, 1, 100]],
        run_live_result=LiveSignalResult(
            last_bar_time=bar_time,
            signals=[
                LiveSignal(
                    action="entry",
                    direction="long",
                    trade_id="L",
                    qty=1.0,
                    sequence_no=0,
                    comment="",
                ),
            ],
            strategy_state_report={"open_trades": {"L": {"qty": 1.0}}},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
        ),
    )

    apply_async_spy = MagicMock()
    monkeypatch.setattr(
        live_signal_module.dispatch_live_signal_event_task, "apply_async", apply_async_spy
    )
    publisher = AsyncMock()
    monkeypatch.setattr(live_signal_module, "publish_realtime", publisher)

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    assert res["events_inserted"] == 1
    # LESSON-019 — claim UPDATE + insert + state upsert 한 commit
    sess_repo.commit.assert_awaited_once()
    sess_repo.upsert_state.assert_awaited_once()
    event_repo.insert_pending_events.assert_awaited_once()
    publisher.assert_awaited_once_with(
        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
    )
    # dispatch task 1건 enqueue
    apply_async_spy.assert_called_once()
    enqueued_args = apply_async_spy.call_args.kwargs.get("args") or apply_async_spy.call_args.args
    # args=[event_id_str]
    assert str(new_event_id) in (
        enqueued_args[0] if isinstance(enqueued_args, list) else enqueued_args
    )


# ── _async_evaluate_all — empty due list ─────────────────────────────


@pytest.mark.asyncio
async def test_empty_due_list_no_error(monkeypatch: pytest.MonkeyPatch) -> None:
    sess_repo = AsyncMock()
    sess_repo.list_active_due = AsyncMock(return_value=[])
    event_repo = AsyncMock()
    event_repo.list_pending = AsyncMock(return_value=[])

    session = AsyncMock()
    engine, sm_factory = _make_engine_sm_mocks(session)
    monkeypatch.setattr(
        live_signal_module, "create_worker_engine_and_sm", lambda: (engine, sm_factory)
    )

    import src.trading.repositories.live_signal_event_repository as event_repo_mod
    import src.trading.repositories.live_signal_session_repository as sess_repo_mod

    monkeypatch.setattr(
        sess_repo_mod, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
    )
    monkeypatch.setattr(
        event_repo_mod, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
    )

    res = await live_signal_module._async_evaluate_all()
    assert res == {"due_count": 0, "evaluated": 0}


# ── BL-362 — divergence observability (money-path fail-closed) ───────────


def _build_strategy(
    strategy_id: Any,
    *,
    pine_source: str,
    position_size_pct: float = 10.0,
    leverage: float = 2.0,
    trading_sessions: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=strategy_id,
        settings={
            "leverage": leverage,
            "margin_mode": "cross",
            "position_size_pct": position_size_pct,
        },
        pine_source=pine_source,
        trading_sessions=trading_sessions or [],
    )


def _demo_account_repo() -> AsyncMock:
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )
    return account_repo


def _preflight_scaffold(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pine_source: str,
    equity_baseline_usdt: Decimal | None = Decimal("8192.00"),
    position_size_pct: float = 10.0,
    leverage: float = 2.0,
    trading_sessions: list[str] | None = None,
    account_repo: AsyncMock | None = None,
    ohlcv_rows: list[list[Any]] | None = None,
    carry_result: tuple[Decimal, int] = (Decimal("0"), 0),
    ledger_result: tuple[Decimal, int] | None = None,
) -> tuple[SimpleNamespace, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    """G4b preflight와 실제 run_live 배선 테스트용 최소 공통 조립."""
    sess = _build_session_obj(equity_baseline_usdt=equity_baseline_usdt)
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.get_state = AsyncMock(return_value=None)
    sess_repo.upsert_state = AsyncMock()
    sess_repo.commit = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(
            sess.strategy_id,
            pine_source=pine_source,
            position_size_pct=position_size_pct,
            leverage=leverage,
            trading_sessions=trading_sessions,
        )
    )
    event_repo = AsyncMock()
    event_repo.list_by_session = AsyncMock(return_value=[])
    event_repo.insert_pending_events = AsyncMock(return_value=[])
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=event_repo,
        account_repo=account_repo if account_repo is not None else _demo_account_repo(),
        strategy_repo=strategy_repo,
        ohlcv_rows=ohlcv_rows or [[int(datetime(2026, 5, 1, tzinfo=UTC).timestamp() * 1000), 1, 2, 0, 1, 100]],
        carry_result=carry_result,
        ledger_result=ledger_result,
    )
    monkeypatch.setattr(
        live_signal_module,
        "send_rule_alert",
        AsyncMock(return_value={"slack": True, "telegram": True}),
    )
    publisher = AsyncMock()
    monkeypatch.setattr(live_signal_module, "publish_realtime", publisher)
    provider = celery_module.get_ccxt_provider_for_worker()
    return sess, sess_repo, event_repo, publisher, provider


def _divergence_scaffold(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pine_source: str,
    run_live_result: LiveSignalResult,
    deactivate_rows: int,
) -> tuple[SimpleNamespace, AsyncMock, AsyncMock, MagicMock, AsyncMock, AsyncMock]:
    """runtime-net 테스트 공통 scaffold. (sess, sess_repo, event_repo, apply_async_spy, mock_alert, publisher)."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=deactivate_rows)
    sess_repo.get_state = AsyncMock(return_value=None)
    sess_repo.upsert_state = AsyncMock()
    sess_repo.commit = AsyncMock()

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(sess.strategy_id, pine_source=pine_source)
    )
    event_repo = AsyncMock()
    event_repo.list_by_session = AsyncMock(return_value=[])
    event_repo.insert_pending_events = AsyncMock(return_value=[])

    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    bar_ms = int(bar_time.timestamp() * 1000)
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=event_repo,
        account_repo=_demo_account_repo(),
        strategy_repo=strategy_repo,
        ohlcv_rows=[[bar_ms, 1, 2, 0, 1, 100]],
        run_live_result=run_live_result,
    )
    apply_async_spy = MagicMock()
    monkeypatch.setattr(
        live_signal_module.dispatch_live_signal_event_task, "apply_async", apply_async_spy
    )
    mock_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(live_signal_module, "send_rule_alert", mock_alert)
    publisher = AsyncMock()
    monkeypatch.setattr(live_signal_module, "publish_realtime", publisher)
    return sess, sess_repo, event_repo, apply_async_spy, mock_alert, publisher


# T3a — classifier ------------------------------------------------------


@pytest.mark.parametrize(
    "msg,expected",
    [
        ("Undefined name: undefined_var", "undefined_name"),
        ("Attribute access not supported: ta.supertrend", "unsupported_attr"),
        ("Call to 'ta.ewma' not supported in current scope", "unsupported_call"),
        ("math function not supported: gamma", "unsupported_call"),
        ("Unsupported BinOp: MatMult", "unsupported_node"),
        ("Unsupported expression node: Lambda", "unsupported_node"),
        ("Subscript on non-Name expression not supported", "unsupported_node"),
        ("var/varip with tuple destructuring is not supported", "unsupported_node"),
        ("something totally weird happened", "unexpected"),
    ],
)
def test_classify_live_divergence_mapping(msg: str, expected: str) -> None:
    assert live_signal_module._classify_live_divergence(msg) == expected


def test_classify_live_divergence_bounded_enum() -> None:
    """category 는 항상 bounded 5-enum 안 (raw 심볼 cardinality 누출 방지)."""
    valid = {
        "undefined_name",
        "unsupported_attr",
        "unsupported_call",
        "unsupported_node",
        "unexpected",
    }
    samples = [
        "Undefined name: x",
        "Attribute access not supported: a.b",
        "Call to 'f' not supported in current scope",
        "Unsupported BinOp: X",
        "Subscript on non-Name expression not supported",
        "totally novel error text",
    ]
    for m in samples:
        assert live_signal_module._classify_live_divergence(m) in valid


# T3b — alert helper ----------------------------------------------------


@pytest.mark.asyncio
async def test_alert_live_divergence_fires_critical(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, Any]] = []

    async def fake_alert(
        settings: Any, *, channel: AlertChannel, title: str, message: str, context: Any
    ) -> dict[str, bool]:
        sent.append({"channel": channel, "title": title, "message": message, "context": context})
        return {"slack": True, "telegram": True}

    monkeypatch.setattr(live_signal_module, "send_rule_alert", fake_alert)
    sid = uuid4()
    await live_signal_module._alert_live_divergence(
        session_id=sid,
        stage="runtime",
        category="undefined_name",
        raw_msg="Undefined name: undefined_var",
        error_count=5,
        last_error_bar=299,
    )
    assert len(sent) == 1
    # 사용자 본인 Pine 심볼은 actionable 차원에서 Slack 메시지에 포함 (시크릿 아님).
    assert "undefined_var" in sent[0]["message"]
    assert sent[0]["channel"] == AlertChannel.both
    ctx = sent[0]["context"]
    assert ctx["category"] == "undefined_name"
    assert ctx["session_id"] == str(sid)[:8]
    assert ctx["error_count"] == "5"


@pytest.mark.asyncio
async def test_alert_live_divergence_truncates_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []

    async def fake_alert(
        settings: Any, *, channel: AlertChannel, title: str, message: str, context: Any
    ) -> dict[str, bool]:
        sent.append(message)
        return {"slack": True, "telegram": True}

    monkeypatch.setattr(live_signal_module, "send_rule_alert", fake_alert)
    await live_signal_module._alert_live_divergence(
        session_id=uuid4(),
        stage="preflight",
        category="coverage_unrunnable",
        raw_msg="X" * 500,
        error_count=0,
        last_error_bar=-1,
    )
    # raw_msg 는 200자 truncate (defense-in-depth).
    assert "X" * 201 not in sent[0]


# T3c — runtime safety net + LESSON-019 commit-spy ----------------------


@pytest.mark.asyncio
async def test_runtime_divergence_deactivates_and_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_live.errors 비어있지 않음 → 세션 비활성화 + events/dispatch 차단 + metric/alert."""
    run_live_result = LiveSignalResult(
        last_bar_time=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        signals=[],
        strategy_state_report={},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
        errors=[(299, "Call to 'ta.alma' not supported in current scope")],
    )
    sess, sess_repo, event_repo, apply_async_spy, mock_alert, publisher = _divergence_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        run_live_result=run_live_result,
        deactivate_rows=1,
    )
    before = _divergence_count("runtime", "unsupported_call")
    before_blocked = qb_live_signal_evaluated_total.labels(
        interval="1m", outcome="divergence_blocked"
    )._value.get()

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "runtime_divergence", "category": "unsupported_call"}
    # fail-closed: 비활성화 + claim/deactivate 단일 commit, events/state/dispatch 전부 차단
    sess_repo.deactivate.assert_awaited_once()
    sess_repo.commit.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()
    sess_repo.upsert_state.assert_not_called()
    apply_async_spy.assert_not_called()
    publisher.assert_awaited_once_with(
        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
    )
    assert mock_alert.call_count == 1
    assert _divergence_count("runtime", "unsupported_call") == before + 1
    after_blocked = qb_live_signal_evaluated_total.labels(
        interval="1m", outcome="divergence_blocked"
    )._value.get()
    assert after_blocked == before_blocked + 1


# T3d — exactly-once (lost deactivate race) -----------------------------


@pytest.mark.asyncio
async def test_runtime_divergence_rows_zero_no_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """deactivate rowcount=0 (동시 worker 가 먼저 비활성화) → alert/metric 미발생."""
    run_live_result = LiveSignalResult(
        last_bar_time=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        signals=[],
        strategy_state_report={},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
        errors=[(299, "Call to 'ta.alma' not supported in current scope")],
    )
    sess, sess_repo, _event_repo, _apply, mock_alert, publisher = _divergence_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        run_live_result=run_live_result,
        deactivate_rows=0,
    )
    before = _divergence_count("runtime", "unsupported_call")

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "runtime_divergence", "category": "unsupported_call"}
    sess_repo.deactivate.assert_awaited_once()
    sess_repo.commit.assert_awaited_once()
    assert mock_alert.call_count == 0
    assert _divergence_count("runtime", "unsupported_call") == before  # 미증가
    publisher.assert_not_awaited()  # winner-only 대칭 — rows==0 은 발행도 없어야 한다


# T3e — preflight (coverage / degraded / non-demo ordering) -------------


@pytest.mark.asyncio
async def test_preflight_unrunnable_deactivates_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """미지원 builtin → fetch/claim 전에 세션 비활성화 + preflight metric/alert."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.commit = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(
            sess.strategy_id, pine_source="//@version=5\nstrategy('t')\nx = ta.ewma(close, 10)\n"
        )
    )
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=_demo_account_repo(),
        strategy_repo=strategy_repo,
        ohlcv_rows=[[1, 1, 2, 0, 1, 100]],
    )
    mock_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(live_signal_module, "send_rule_alert", mock_alert)
    publisher = AsyncMock()
    monkeypatch.setattr(live_signal_module, "publish_realtime", publisher)
    provider = celery_module.get_ccxt_provider_for_worker()
    before = _divergence_count("preflight", "coverage_unrunnable")

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "coverage_unrunnable"}
    sess_repo.deactivate.assert_awaited_once()
    sess_repo.commit.assert_awaited_once()
    sess_repo.try_claim_bar.assert_not_called()  # preflight 가 claim 전에 차단
    provider.fetch_ohlcv.assert_not_called()  # OHLCV fetch 전에 차단
    assert mock_alert.call_count == 1
    assert _divergence_count("preflight", "coverage_unrunnable") == before + 1
    publisher.assert_awaited_once_with(
        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
    )


@pytest.mark.asyncio
async def test_preflight_degraded_deactivates(monkeypatch: pytest.MonkeyPatch) -> None:
    """degraded(request.security 등 — graceful 이나 결과 divergence) → fail-closed 비활성화."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.commit = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(
            sess.strategy_id,
            pine_source=(
                "//@version=5\nstrategy('t')\nz = request.security(syminfo.tickerid, '60', close)\n"
            ),
        )
    )
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=_demo_account_repo(),
        strategy_repo=strategy_repo,
        ohlcv_rows=[[1, 1, 2, 0, 1, 100]],
    )
    mock_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(live_signal_module, "send_rule_alert", mock_alert)
    before = _divergence_count("preflight", "degraded_unconsented")

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "degraded_unconsented"}
    sess_repo.deactivate.assert_awaited_once()
    assert mock_alert.call_count == 1
    assert _divergence_count("preflight", "degraded_unconsented") == before + 1


@pytest.mark.asyncio
async def test_preflight_non_demo_skips_not_deactivated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G1 P1#2 — account/demo check 가 preflight 보다 먼저. non-demo 는 skip(비활성화 X)."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.deactivate = AsyncMock(return_value=1)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(
            sess.strategy_id, pine_source="//@version=5\nstrategy('t')\nx = ta.ewma(close, 10)\n"
        )
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.live)
    )
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        ohlcv_rows=[[1, 1, 2, 0, 1, 100]],
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res == {"skipped": "non_demo_account"}
    sess_repo.deactivate.assert_not_called()  # 미지원 Pine 이라도 non-demo 는 비활성화 X


@pytest.mark.asyncio
async def test_preflight_deactivates_stop_entry_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stop= 진입 세션은 OHLCV fetch 전에 자동 비활성화한다."""
    sess, sess_repo, _event_repo, publisher, provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_STOP_ENTRY_SOURCE,
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res == {"deactivated": "stop_entry_unsupported"}
    sess_repo.deactivate.assert_awaited_once()
    publisher.assert_awaited_once_with(
        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
    )
    provider.fetch_ohlcv.assert_not_called()


@pytest.mark.asyncio
async def test_preflight_stop_entry_does_not_increment_divergence_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """예상 가능한 stop-entry 종료는 page용 divergence counter를 올리지 않는다."""
    sess, _sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_STOP_ENTRY_SOURCE,
    )
    before_divergence = _divergence_count("preflight", "stop_entry_unsupported")
    before_skipped = qb_live_signal_skipped_total.labels(
        reason="stop_entry_unsupported"
    )._value.get()

    await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert _divergence_count("preflight", "stop_entry_unsupported") == before_divergence
    assert qb_live_signal_skipped_total.labels(reason="stop_entry_unsupported")._value.get() == (
        before_skipped + 1
    )


@pytest.mark.asyncio
async def test_preflight_deactivates_null_equity_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """시장가 전략이라도 마이그레이션 이전 NULL 기준선은 비활성화한다."""
    sess, sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_MARKET_ENTRY_SOURCE,
        equity_baseline_usdt=None,
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res == {"deactivated": "equity_baseline_missing"}
    sess_repo.deactivate.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "carry_pnl",
    [Decimal("-8192.00"), Decimal("NaN")],
    ids=["zero", "nan"],
)
async def test_effective_capital_exhaustion_deactivates_without_divergence(
    monkeypatch: pytest.MonkeyPatch, carry_pnl: Decimal
) -> None:
    """0 이하 또는 비유한 실효 자본은 주문 전에 page 없이 세션을 종료한다."""
    window_start = datetime(2026, 5, 1, 11, 58, tzinfo=UTC)
    sess, sess_repo, event_repo, publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_MARKET_ENTRY_SOURCE,
        carry_result=(carry_pnl, 1),
        ohlcv_rows=[
            [int(window_start.timestamp() * 1000), 1, 1, 1, 1, 100],
            [int(datetime(2026, 5, 1, 11, 59, tzinfo=UTC).timestamp() * 1000), 1, 1, 1, 1, 100],
            [int(datetime(2026, 5, 1, 12, 0, tzinfo=UTC).timestamp() * 1000), 1, 1, 1, 1, 100],
        ],
    )
    alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(live_signal_module, "send_rule_alert", alert)
    before_divergence = _divergence_count("preflight", "equity_exhausted")
    before_skipped = qb_live_signal_skipped_total.labels(reason="equity_exhausted")._value.get()

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "equity_exhausted"}
    event_repo.sum_realized_pnl_before.assert_awaited_once_with(sess.id, bar_time=window_start)
    sess_repo.try_claim_bar.assert_not_awaited()
    sess_repo.deactivate.assert_awaited_once()
    publisher.assert_awaited_once_with(
        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
    )
    assert alert.await_count == 1
    assert _divergence_count("preflight", "equity_exhausted") == before_divergence
    assert qb_live_signal_skipped_total.labels(reason="equity_exhausted")._value.get() == (
        before_skipped + 1
    )


@pytest.mark.asyncio
async def test_carry_query_error_does_not_deactivate_as_run_live_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """carry 조회 오류는 Pine 인터프리터 발산으로 분류하거나 세션을 종료하지 않는다."""
    window_start = datetime(2026, 5, 1, 11, 58, tzinfo=UTC)
    sess, sess_repo, event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_MARKET_ENTRY_SOURCE,
        ohlcv_rows=[
            [int(window_start.timestamp() * 1000), 1, 1, 1, 1, 100],
            [int(datetime(2026, 5, 1, 11, 59, tzinfo=UTC).timestamp() * 1000), 1, 1, 1, 1, 100],
            [int(datetime(2026, 5, 1, 12, 0, tzinfo=UTC).timestamp() * 1000), 1, 1, 1, 1, 100],
        ],
    )
    event_repo.sum_realized_pnl_before.side_effect = ConnectionError("database unavailable")
    before_divergence = _divergence_count("runtime", "run_live_error")

    with pytest.raises(ConnectionError, match="database unavailable"):
        await live_signal_module._evaluate_session_inner(sess.id, "1m")

    event_repo.sum_realized_pnl_before.assert_awaited_once_with(sess.id, bar_time=window_start)
    sess_repo.try_claim_bar.assert_not_awaited()
    sess_repo.deactivate.assert_not_awaited()
    assert _divergence_count("runtime", "run_live_error") == before_divergence


@pytest.mark.asyncio
async def test_market_entry_session_with_baseline_passes_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조군은 기준선이 있는 시장가 전략이 preflight를 통과함을 고정한다."""
    sess, sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_MARKET_ENTRY_SOURCE,
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    sess_repo.deactivate.assert_not_called()


@pytest.mark.asyncio
async def test_coverage_unrunnable_wins_over_stop_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """미지원 builtin과 stop=이 함께 있으면 coverage_unrunnable이 우선한다."""
    source = (
        "//@version=5\nstrategy('t')\nx = ta.ewma(close, 10)\n"
        "strategy.entry('L', strategy.long, stop=close)\n"
    )
    sess, _sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=source,
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res == {"deactivated": "coverage_unrunnable"}


@pytest.mark.asyncio
async def test_non_demo_account_still_skips_not_deactivates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """non-demo stop-entry 세션도 기존 계약대로 skip만 하고 비활성화하지 않는다."""
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.live)
    )
    sess, sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_STOP_ENTRY_SOURCE,
        account_repo=account_repo,
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res == {"skipped": "non_demo_account"}
    sess_repo.deactivate.assert_not_called()


@pytest.mark.asyncio
async def test_live_sizing_carry_restores_window_invariance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-486 손계산 오라클로 task carry 배선을 실제 `run_live`까지 검증한다.

    baseline 8192 + carry 4096 = 12288, pct 50, price 65536.
    정답은 12288 x 50 / 100 / 65536 = 0.09375다.
    carry 무시는 0.0625, carry 이중계상은 0.125, 미배선 fallback은 1.0이다.
    네 값이 서로 달라 오답이 정답을 통과할 수 없다.
    """
    import src.strategy.pine_v2.event_loop as event_loop_mod

    real_run_live = event_loop_mod.run_live
    source = (
        "//@version=5\nstrategy('last bar market entry')\n"
        "if close > open\n    strategy.entry('L', strategy.long)\n"
    )
    window_start = datetime(2026, 5, 1, 11, 58, tzinfo=UTC)
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, _sess_repo, event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=source,
        equity_baseline_usdt=Decimal("8192.00"),
        position_size_pct=50.0,
        carry_result=(Decimal("4096"), 1),
        ohlcv_rows=[
            [int(window_start.timestamp() * 1000), 65535.0, 65535.0, 65535.0, 65535.0, 100],
            [int(datetime(2026, 5, 1, 11, 59, tzinfo=UTC).timestamp() * 1000), 65535.0, 65535.0, 65535.0, 65535.0, 100],
            [int(bar_time.timestamp() * 1000), 65535.0, 65536.0, 65535.0, 65536.0, 100],
        ],
    )
    monkeypatch.setattr(event_loop_mod, "run_live", real_run_live)

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    event_repo.sum_realized_pnl_before.assert_awaited_once_with(sess.id, bar_time=window_start)
    signals = event_repo.insert_pending_events.await_args.kwargs["signals"]
    assert signals[0]["qty"] == 0.09375
    state_kwargs = _sess_repo.upsert_state.await_args.kwargs
    assert state_kwargs["total_closed_trades"] == 1
    assert state_kwargs["total_realized_pnl"] == Decimal("4096")


@pytest.mark.asyncio
async def test_live_sizing_passes_carry_to_initial_capital_and_ledger_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """carry는 initial_capital에만 반영하고 화면 총계는 원장 합계를 사용한다."""
    import src.strategy.pine_v2.event_loop as event_loop_mod

    window_start = datetime(2026, 5, 1, 11, 58, tzinfo=UTC)
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        carry_result=(Decimal("4096"), 1),
        ledger_result=(Decimal("6"), 2),
        ohlcv_rows=[
            [int(window_start.timestamp() * 1000), 1, 2, 0, 1, 100],
            [int(datetime(2026, 5, 1, 11, 59, tzinfo=UTC).timestamp() * 1000), 1, 2, 0, 1, 100],
            [int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100],
        ],
    )
    captured_initial_capital: list[float] = []

    def fake_run_live(*_args: object, **kwargs: object) -> LiveSignalResult:
        captured_initial_capital.append(float(kwargs["initial_capital"]))
        return LiveSignalResult(
            last_bar_time=bar_time,
            signals=[],
            strategy_state_report={},
            total_closed_trades=2,
            total_realized_pnl=Decimal("8"),
        )

    monkeypatch.setattr(event_loop_mod, "run_live", fake_run_live)

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    _event_repo.sum_realized_pnl_before.assert_awaited_once_with(sess.id, bar_time=window_start)
    _event_repo.sum_realized_pnl_all.assert_awaited_once_with(sess.id)
    assert captured_initial_capital == [12288.0]
    state_kwargs = sess_repo.upsert_state.await_args.kwargs
    assert state_kwargs["total_closed_trades"] == 2
    assert state_kwargs["total_realized_pnl"] == Decimal("6")


@pytest.mark.asyncio
async def test_run_live_passes_leverage_and_counts_engine_events_without_divergence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-483. 정상 skip과 모델 청산은 page나 세션 중단 없이 따로 관측한다."""
    import src.strategy.pine_v2.event_loop as event_loop_mod

    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=_MARKET_ENTRY_SOURCE,
        leverage=8.0,
        ohlcv_rows=[[int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100]],
    )
    captured_kwargs: list[dict[str, object]] = []
    entry_skips = [
        {"bar_index": 0, "reason": "margin_insufficient", "trade_id": "M"},
        {"bar_index": 0, "reason": "non_finite_qty", "trade_id": "N"},
        {"bar_index": 0, "reason": "pyramiding_cap", "trade_id": "P"},
        {"bar_index": 0, "reason": "session_closed", "trade_id": "S"},
        {"bar_index": 0, "reason": "unexpected_reason", "trade_id": "U"},
    ]

    def fake_run_live(*_args: object, **kwargs: object) -> LiveSignalResult:
        captured_kwargs.append(kwargs)
        return LiveSignalResult(
            last_bar_time=bar_time,
            signals=[],
            strategy_state_report={"last_bar_entry_skips": entry_skips},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
            entry_skips=entry_skips,
            liquidations=[{"direction": "long"}, {"direction": "short"}],
        )

    monkeypatch.setattr(event_loop_mod, "run_live", fake_run_live)
    entry_skip_counter = getattr(live_signal_module, "qb_live_signal_entry_skipped_total")
    liquidation_counter = getattr(live_signal_module, "qb_live_signal_liquidation_total")
    reasons = [
        "margin_insufficient",
        "non_finite_qty",
        "pyramiding_cap",
        "session_closed",
        "other",
    ]
    before_skips = {
        reason: entry_skip_counter.labels(reason=reason)._value.get() for reason in reasons
    }
    before_divergence = _divergence_total()
    before_liquidations = {
        direction: liquidation_counter.labels(direction=direction)._value.get()
        for direction in ("long", "short")
    }

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    assert captured_kwargs == [
        {
            "initial_capital": 8192.0,
            "live_position_size_pct": 10.0,
            "leverage": 8.0,
            "sessions_allowed": (),
            "pyramiding": None,
        }
    ]
    for reason in reasons:
        assert entry_skip_counter.labels(reason=reason)._value.get() == before_skips[reason] + 1
    for direction in ("long", "short"):
        assert liquidation_counter.labels(direction=direction)._value.get() == (
            before_liquidations[direction] + 1
        )
    assert _divergence_total() == before_divergence
    sess_repo.deactivate.assert_not_called()


@pytest.mark.asyncio
async def test_run_live_passes_sessions_and_declared_pyramiding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-481/482. 전략 SSOT의 세션과 Pine 선언 cap을 그대로 run_live로 전달한다."""
    import src.strategy.pine_v2.event_loop as event_loop_mod

    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, _sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x', pyramiding=2)",
        trading_sessions=["asia", "ny"],
        ohlcv_rows=[[int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100]],
    )
    captured_kwargs: list[dict[str, object]] = []

    def fake_run_live(*_args: object, **kwargs: object) -> LiveSignalResult:
        captured_kwargs.append(kwargs)
        return LiveSignalResult(
            last_bar_time=bar_time,
            signals=[],
            strategy_state_report={},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
        )

    monkeypatch.setattr(event_loop_mod, "run_live", fake_run_live)

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    assert captured_kwargs == [
        {
            "initial_capital": 8192.0,
            "live_position_size_pct": 10.0,
            "leverage": 2.0,
            "sessions_allowed": ("asia", "ny"),
            "pyramiding": 2,
        }
    ]


@pytest.mark.asyncio
async def test_live_sizing_reaches_run_live_hand_computed(monkeypatch: pytest.MonkeyPatch) -> None:
    """8192 x 50 / 100 / 65536 = 0.0625인 carry=0 음성 대조군을 보존한다."""
    import src.strategy.pine_v2.event_loop as event_loop_mod

    real_run_live = event_loop_mod.run_live
    source = (
        "//@version=5\nstrategy('last bar market entry')\n"
        "if close > open\n    strategy.entry('L', strategy.long)\n"
    )
    window_start = datetime(2026, 5, 1, 11, 58, tzinfo=UTC)
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, _sess_repo, event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source=source,
        equity_baseline_usdt=Decimal("8192.00"),
        position_size_pct=50.0,
        carry_result=(Decimal("0"), 0),
        ohlcv_rows=[
            [int(window_start.timestamp() * 1000), 65535.0, 65535.0, 65535.0, 65535.0, 100],
            [int(datetime(2026, 5, 1, 11, 59, tzinfo=UTC).timestamp() * 1000), 65535.0, 65535.0, 65535.0, 65535.0, 100],
            [int(bar_time.timestamp() * 1000), 65535.0, 65536.0, 65535.0, 65536.0, 100],
        ],
    )
    monkeypatch.setattr(event_loop_mod, "run_live", real_run_live)

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    event_repo.sum_realized_pnl_before.assert_awaited_once_with(sess.id, bar_time=window_start)
    signals = event_repo.insert_pending_events.await_args.kwargs["signals"]
    assert signals[0]["qty"] == 0.0625


@pytest.mark.asyncio
async def test_effective_capital_uses_decimal_sum_before_float_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1000.07과 0.1은 Decimal에서 더한 뒤 한 번만 float으로 넘긴다."""
    import src.strategy.pine_v2.event_loop as event_loop_mod

    window_start = datetime(2026, 5, 1, 11, 58, tzinfo=UTC)
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, _sess_repo, event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        equity_baseline_usdt=Decimal("1000.07"),
        carry_result=(Decimal("0.1"), 1),
        ohlcv_rows=[
            [int(window_start.timestamp() * 1000), 1, 2, 0, 1, 100],
            [int(datetime(2026, 5, 1, 11, 59, tzinfo=UTC).timestamp() * 1000), 1, 2, 0, 1, 100],
            [int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100],
        ],
    )
    captured_initial_capital: list[float] = []

    def fake_run_live(*_args: object, **kwargs: object) -> LiveSignalResult:
        captured_initial_capital.append(float(kwargs["initial_capital"]))
        return LiveSignalResult(
            last_bar_time=bar_time,
            signals=[],
            strategy_state_report={},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
        )

    monkeypatch.setattr(event_loop_mod, "run_live", fake_run_live)

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    event_repo.sum_realized_pnl_before.assert_awaited_once_with(sess.id, bar_time=window_start)
    assert captured_initial_capital == [1000.17]


@pytest.mark.asyncio
async def test_d2_ledger_is_ssot_while_sizing_remains_a_known_limitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D2 프로덕션 회귀다. 16:12의 3건 5.16879987이 16:49에 2건 4.07002377로 줄었다.

    화면 총계는 원장 SSOT로 해결됐고 사이징 자본만 남았다. 창 밖 진입의 창 안 close가
    재현되지 않는 동안 initial_capital은 일시적으로 함몰한다.
    """
    import src.strategy.pine_v2.event_loop as event_loop_mod

    real_run_live = event_loop_mod.run_live
    first_window_start = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    second_window_start = datetime(2026, 5, 1, 12, 3, tzinfo=UTC)
    source = (
        "//@version=5\nstrategy('cross window close')\n"
        "if close == 100\n    strategy.entry('A', strategy.long)\n"
        "if close == 200\n    strategy.close('A')\n"
    )
    sess, sess_repo, event_repo, _publisher, provider = _preflight_scaffold(
        monkeypatch,
        pine_source=source,
        carry_result=(Decimal("0"), 0),
        ohlcv_rows=[
            [int(first_window_start.timestamp() * 1000), 101, 101, 101, 101, 100],
            [int(datetime(2026, 5, 1, 12, 1, tzinfo=UTC).timestamp() * 1000), 200, 200, 200, 200, 100],
            [int(datetime(2026, 5, 1, 12, 2, tzinfo=UTC).timestamp() * 1000), 300, 300, 300, 300, 100],
        ],
    )
    provider.fetch_ohlcv.side_effect = [
        [
            [int(first_window_start.timestamp() * 1000), 101, 101, 101, 101, 100],
            [int(datetime(2026, 5, 1, 12, 1, tzinfo=UTC).timestamp() * 1000), 200, 200, 200, 200, 100],
            [int(datetime(2026, 5, 1, 12, 2, tzinfo=UTC).timestamp() * 1000), 300, 300, 300, 300, 100],
        ],
        [
            [int(second_window_start.timestamp() * 1000), 301, 301, 301, 301, 100],
            [int(datetime(2026, 5, 1, 12, 4, tzinfo=UTC).timestamp() * 1000), 302, 302, 302, 302, 100],
            [int(datetime(2026, 5, 1, 12, 5, tzinfo=UTC).timestamp() * 1000), 303, 303, 303, 303, 100],
        ],
    ]
    event_repo.sum_realized_pnl_before.side_effect = [
        (Decimal("0"), 0),
        (Decimal("4096"), 1),
    ]
    event_repo.sum_realized_pnl_all.side_effect = [
        (Decimal("4096"), 1),
        (Decimal("4096"), 1),
    ]
    initial_capitals: list[float] = []

    def capture_run_live(*args: object, **kwargs: object) -> LiveSignalResult:
        initial_capitals.append(float(kwargs["initial_capital"]))
        return real_run_live(*args, **kwargs)

    monkeypatch.setattr(event_loop_mod, "run_live", capture_run_live)

    first = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    second = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert first["evaluated"] is True
    assert second["evaluated"] is True
    assert [
        call.kwargs["bar_time"] for call in event_repo.sum_realized_pnl_before.await_args_list
    ] == [first_window_start, second_window_start]
    assert initial_capitals == [8192.0, 12288.0]
    assert [
        call.kwargs["total_realized_pnl"] for call in sess_repo.upsert_state.await_args_list
    ] == [Decimal("4096"), Decimal("4096")]


@pytest.mark.asyncio
async def test_d2_ledger_is_ssot_when_run_live_loses_a_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D2 프로덕션 회귀다. 16:12에는 3건 5.16879987, 16:49에는 2건 4.07002377이었다.

    warmup replay가 2인 close 1건만 반환해도 append-only 원장에 6인 2건이 있으면
    화면 상태는 원장 총계를 유지해야 한다.
    """
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, sess_repo, event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        ledger_result=(Decimal("6"), 2),
        ohlcv_rows=[[int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100]],
    )
    import src.strategy.pine_v2.event_loop as event_loop_mod

    monkeypatch.setattr(
        event_loop_mod,
        "run_live",
        lambda *_args, **_kwargs: LiveSignalResult(
            last_bar_time=bar_time,
            signals=[],
            strategy_state_report={},
            total_closed_trades=1,
            total_realized_pnl=Decimal("2"),
        ),
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    event_repo.sum_realized_pnl_all.assert_awaited_once_with(sess.id)
    state_kwargs = sess_repo.upsert_state.await_args.kwargs
    assert state_kwargs["total_realized_pnl"] == Decimal("6")
    assert state_kwargs["total_closed_trades"] == 2


@pytest.mark.asyncio
async def test_equity_curve_does_not_grow_without_new_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """warmup 재계산 총손익이 변해도 새 close event 없이는 curve를 갱신하지 않는다."""
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, sess_repo, _event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        ohlcv_rows=[[int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100]],
    )
    sess_repo.get_state = AsyncMock(
        return_value=SimpleNamespace(
            total_realized_pnl=Decimal("1"),
            equity_curve=[{"timestamp_ms": 1, "cumulative_pnl": "1"}],
        )
    )

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    assert sess_repo.upsert_state.await_args.kwargs["equity_curve"] is None


@pytest.mark.asyncio
async def test_equity_curve_grows_once_for_new_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """새 close event 한 건은 curve point를 정확히 한 건만 추가한다."""
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    sess, sess_repo, event_repo, _publisher, _provider = _preflight_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        ohlcv_rows=[[int(bar_time.timestamp() * 1000), 1, 2, 0, 1, 100]],
    )
    sess_repo.get_state = AsyncMock(
        return_value=SimpleNamespace(
            equity_curve=[{"timestamp_ms": 1, "cumulative_pnl": "1"}],
        )
    )
    close_event = SimpleNamespace(
        id=uuid4(),
        bar_time=bar_time,
        sequence_no=0,
        action="close",
        trade_id="L",
        realized_pnl=Decimal("2"),
        status=LiveSignalEventStatus.pending,
    )
    event_repo.insert_pending_events = AsyncMock(return_value=[close_event])
    import src.strategy.pine_v2.event_loop as event_loop_mod

    monkeypatch.setattr(
        event_loop_mod,
        "run_live",
        lambda *_args, **_kwargs: LiveSignalResult(
            last_bar_time=bar_time,
            signals=[
                LiveSignal(
                    action="close",
                    direction="long",
                    trade_id="L",
                    qty=1.0,
                    sequence_no=0,
                    realized_pnl=Decimal("2"),
                )
            ],
            strategy_state_report={},
            total_closed_trades=1,
            total_realized_pnl=Decimal("2"),
        ),
    )
    monkeypatch.setattr(live_signal_module.dispatch_live_signal_event_task, "apply_async", MagicMock())

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    curve = sess_repo.upsert_state.await_args.kwargs["equity_curve"]
    assert curve == [
        {"timestamp_ms": 1, "cumulative_pnl": "1"},
        {"timestamp_ms": int(bar_time.timestamp() * 1000), "cumulative_pnl": "3"},
    ]


# T3f — regression: clean strategy 정상 경로 불변 ------------------------


@pytest.mark.asyncio
async def test_clean_strategy_no_divergence(monkeypatch: pytest.MonkeyPatch) -> None:
    """clean source + errors=[] → 정상 dispatch, deactivate/alert/divergence-metric 미발생."""
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    run_live_result = LiveSignalResult(
        last_bar_time=bar_time,
        signals=[
            LiveSignal(
                action="entry",
                direction="long",
                trade_id="L",
                qty=1.0,
                sequence_no=0,
                comment="",
            ),
        ],
        strategy_state_report={"open_trades": {"L": {"qty": 1.0}}},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
        errors=[],
    )
    sess, sess_repo, event_repo, apply_async_spy, mock_alert, _publisher = _divergence_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        run_live_result=run_live_result,
        deactivate_rows=1,
    )
    new_event = SimpleNamespace(
        id=uuid4(),
        bar_time=bar_time,
        sequence_no=0,
        action="entry",
        trade_id="L",
        status=LiveSignalEventStatus.pending,
    )
    event_repo.insert_pending_events = AsyncMock(return_value=[new_event])
    before = _divergence_count("runtime", "unsupported_call")

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res["evaluated"] is True
    sess_repo.deactivate.assert_not_called()
    assert mock_alert.call_count == 0
    apply_async_spy.assert_called_once()  # 정상 dispatch 경로 보존
    assert _divergence_count("runtime", "unsupported_call") == before  # divergence 불변


# G2 — run_live 가 result.errors 밖 예외를 raise 하는 경로 (parse/raw arithmetic) ----


@pytest.mark.asyncio
async def test_run_live_crash_deactivates(monkeypatch: pytest.MonkeyPatch) -> None:
    """G2 P1 — run_live 가 result.errors 로 안 잡히는 예외(ZeroDivisionError 등) raise →
    crash-loop 대신 fail-closed 비활성화 (category=run_live_error)."""
    sess, sess_repo, event_repo, apply_async_spy, mock_alert, _publisher = _divergence_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')",
        run_live_result=LiveSignalResult(
            last_bar_time=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            signals=[],
            strategy_state_report={},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
        ),
        deactivate_rows=1,
    )
    import src.strategy.pine_v2.event_loop as event_loop_mod

    def _boom(*_a: object, **_kw: object) -> Any:
        raise ZeroDivisionError("float division by zero")

    monkeypatch.setattr(event_loop_mod, "run_live", _boom)
    before = _divergence_count("runtime", "run_live_error")

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "run_live_error"}
    sess_repo.deactivate.assert_awaited_once()
    sess_repo.commit.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()
    apply_async_spy.assert_not_called()
    assert mock_alert.call_count == 1
    alert_message = mock_alert.await_args.kwargs["message"]
    assert "ZeroDivisionError" in alert_message
    assert "float division by zero" not in alert_message
    assert _divergence_count("runtime", "run_live_error") == before + 1


@pytest.mark.asyncio
async def test_runtime_divergence_real_run_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """G2 P2#4 — 실제 run_live 통합: undefined_var 는 coverage-runnable 이나 runtime
    PineRuntimeError → result.errors → 비활성화 (mock 이 가리지 않는 end-to-end)."""
    import src.strategy.pine_v2.event_loop as event_loop_mod

    real_run_live = event_loop_mod.run_live  # scaffold 패치 전 캡처
    sess, sess_repo, event_repo, apply_async_spy, mock_alert, _publisher = _divergence_scaffold(
        monkeypatch,
        pine_source="//@version=5\nstrategy('x')\ny = undefined_var + 1\n",
        run_live_result=LiveSignalResult(
            last_bar_time=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            signals=[],
            strategy_state_report={},
            total_closed_trades=0,
            total_realized_pnl=Decimal("0"),
        ),
        deactivate_rows=1,
    )
    monkeypatch.setattr(event_loop_mod, "run_live", real_run_live)  # 실제 run_live 복원

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res["deactivated"] == "runtime_divergence"
    assert res["category"] == "undefined_name"
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()
    apply_async_spy.assert_not_called()
    assert mock_alert.call_count == 1


@pytest.mark.asyncio
async def test_alert_live_divergence_send_failure_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G2 P2#3 — send_rule_alert raise 시 swallow + log (예외 전파 X)."""

    async def boom_alert(
        settings: Any, *, channel: AlertChannel, title: str, message: str, context: Any
    ) -> dict[str, bool]:
        raise RuntimeError("slack down")

    monkeypatch.setattr(live_signal_module, "send_rule_alert", boom_alert)
    # 예외가 전파되면 이 await 가 raise → 테스트 실패. swallow 되면 정상 반환.
    await live_signal_module._alert_live_divergence(
        session_id=uuid4(),
        stage="runtime",
        category="unexpected",
        raw_msg="x",
        error_count=1,
        last_error_bar=-1,
    )


@pytest.mark.asyncio
async def test_preflight_unrunnable_precedence_over_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_runnable=False AND has_degraded=True 동시 → coverage_unrunnable 우선 (precedence)."""
    sess = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.commit = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_build_strategy(
            sess.strategy_id,
            pine_source=(
                "//@version=5\nstrategy('t')\n"
                "x = ta.ewma(close, 10)\n"  # unsupported → is_runnable=False
                "z = request.security(syminfo.tickerid, '60', close)\n"  # degraded
            ),
        )
    )
    _patch_inner_dependencies(
        monkeypatch,
        sess_repo=sess_repo,
        event_repo=AsyncMock(),
        account_repo=_demo_account_repo(),
        strategy_repo=strategy_repo,
        ohlcv_rows=[[1, 1, 2, 0, 1, 100]],
    )
    monkeypatch.setattr(
        live_signal_module,
        "send_rule_alert",
        AsyncMock(return_value={"slack": True, "telegram": True}),
    )
    before = _divergence_count("preflight", "coverage_unrunnable")

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await _flush_pending_alerts()

    assert res == {"deactivated": "coverage_unrunnable"}  # is_runnable=False 우선
    assert _divergence_count("preflight", "coverage_unrunnable") == before + 1


@pytest.mark.asyncio
async def test_async_evaluate_all_isolates_session_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G3 — 한 세션의 uncaught 오류가 batch 전체를 abort 하지 않고 격리 (이후 세션 지속)."""
    s1 = _build_session_obj()
    s2 = _build_session_obj()
    sess_repo = AsyncMock()
    sess_repo.list_active_due = AsyncMock(return_value=[s1, s2])
    event_repo = AsyncMock()
    event_repo.list_pending = AsyncMock(return_value=[])

    session = AsyncMock()
    engine, sm_factory = _make_engine_sm_mocks(session)
    monkeypatch.setattr(
        live_signal_module, "create_worker_engine_and_sm", lambda: (engine, sm_factory)
    )
    import src.trading.repositories.live_signal_event_repository as event_repo_mod
    import src.trading.repositories.live_signal_session_repository as sess_repo_mod

    monkeypatch.setattr(
        sess_repo_mod, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
    )
    monkeypatch.setattr(
        event_repo_mod, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
    )

    calls: list[Any] = []

    async def fake_eval(session_id: Any, interval_value: str) -> dict[str, Any]:
        calls.append(session_id)
        if session_id == s1.id:
            raise RuntimeError("boom")
        return {"evaluated": True}

    monkeypatch.setattr(live_signal_module, "_async_evaluate_session", fake_eval)
    before = qb_live_signal_skipped_total.labels(reason="eval_error")._value.get()

    res = await live_signal_module._async_evaluate_all()

    # batch abort 안 됨 — 두 세션 모두 시도
    assert calls == [s1.id, s2.id]
    assert res["due_count"] == 2
    assert res["evaluated"] == 2
    assert res["results"][0].get("error") == "eval_error"  # 첫 세션 격리
    assert res["results"][1].get("evaluated") is True  # 둘째 정상
    assert qb_live_signal_skipped_total.labels(reason="eval_error")._value.get() == before + 1

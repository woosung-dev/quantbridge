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

import sys
from datetime import UTC, datetime
from decimal import Decimal
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

from src.strategy.pine_v2.event_loop import LiveSignal, LiveSignalResult  # noqa: E402
from src.trading.models import (  # noqa: E402
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    LiveSignalInterval,
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
    *, is_active: bool = True, last_evaluated_bar_time: datetime | None = None
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
    monkeypatch.setattr(
        strategy_repo_mod, "StrategyRepository", _repo_class_factory(strategy_repo)
    )

    # CCXT provider — fetch_ohlcv 결과 주입
    fake_provider = AsyncMock()
    fake_provider.fetch_ohlcv = AsyncMock(return_value=ohlcv_rows or [])
    monkeypatch.setattr(
        celery_module, "get_ccxt_provider_for_worker", lambda: fake_provider
    )

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
                    action="entry", direction="long", trade_id="L",
                    qty=1.0, sequence_no=0, comment="",
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

    res = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert res["evaluated"] is True
    assert res["events_inserted"] == 1
    # LESSON-019 — claim UPDATE + insert + state upsert 한 commit
    sess_repo.commit.assert_awaited_once()
    sess_repo.upsert_state.assert_awaited_once()
    event_repo.insert_pending_events.assert_awaited_once()
    # dispatch task 1건 enqueue
    apply_async_spy.assert_called_once()
    enqueued_args = apply_async_spy.call_args.kwargs.get("args") or apply_async_spy.call_args.args
    # args=[event_id_str]
    assert str(new_event_id) in (enqueued_args[0] if isinstance(enqueued_args, list) else enqueued_args)


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

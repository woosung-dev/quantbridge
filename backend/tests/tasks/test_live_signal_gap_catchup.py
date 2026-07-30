# 라이브 평가 공백 재동기화와 orphan close 백스톱을 검증한다.
"""평가 catch-up과 close 포지션 가드의 Celery 경계 동작을 검증한다."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest

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


class _SessionContext:
    """테스트용 worker AsyncSession context다."""

    def __init__(self, session: AsyncMock) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncMock:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    engine = AsyncMock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(
        live_signal_module,
        "create_worker_engine_and_sm",
        lambda: (engine, lambda: _SessionContext(session)),
    )


def _session(*, last_evaluated_bar_time: datetime | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=True,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        last_evaluated_bar_time=last_evaluated_bar_time,
        equity_baseline_usdt=Decimal("8192"),
    )


def _strategy(strategy_id: object, *, fill_timing: str | None = None) -> SimpleNamespace:
    settings: dict[str, object] = {
        "leverage": 2,
        "margin_mode": "cross",
        "position_size_pct": 10.0,
    }
    if fill_timing is not None:
        settings["fill_timing"] = fill_timing
    return SimpleNamespace(
        id=strategy_id,
        settings=settings,
        pine_source="//@version=5\nstrategy('gap')",
        trading_sessions=[],
    )


def _result(
    *,
    last_bar_time: datetime,
    signals: list[LiveSignal],
    open_trades: list[object] | None = None,
) -> LiveSignalResult:
    return LiveSignalResult(
        last_bar_time=last_bar_time,
        signals=signals,
        strategy_state_report={"open_trades": open_trades or []},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
    )


def _event(signal: LiveSignal, session_id: object) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        session_id=session_id,
        bar_time=signal.bar_time,
        sequence_no=signal.sequence_no,
        action=signal.action,
        trade_id=signal.trade_id,
        status=LiveSignalEventStatus.pending,
        realized_pnl=signal.realized_pnl,
    )


def _install_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sess: SimpleNamespace,
    rows: list[list[object]],
    run_result: LiveSignalResult,
    inserted_events: list[SimpleNamespace],
    fill_timing: str | None = None,
    previous_state: object | None = None,
) -> tuple[AsyncMock, AsyncMock, list[dict[str, Any]]]:
    """평가 경로를 메모리 의존성으로 고정하고 run_live kwargs를 수집한다."""
    _patch_engine(monkeypatch)
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.get_state = AsyncMock(return_value=previous_state)
    sess_repo.upsert_state = AsyncMock()
    sess_repo.commit = AsyncMock()
    event_repo = AsyncMock()
    event_repo.sum_realized_pnl_before = AsyncMock(return_value=(Decimal("0"), 0))
    event_repo.sum_realized_pnl_all = AsyncMock(return_value=(Decimal("0"), 0))
    event_repo.list_by_session = AsyncMock(return_value=[])
    event_repo.insert_pending_events = AsyncMock(return_value=inserted_events)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=_strategy(sess.strategy_id, fill_timing=fill_timing)
    )
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )

    import src.strategy.pine_v2.event_loop as event_loop_module
    import src.strategy.repository as strategy_repo_module
    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.live_signal_event_repository as event_repo_module
    import src.trading.repositories.live_signal_session_repository as sess_repo_module

    monkeypatch.setattr(
        sess_repo_module, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
    )
    monkeypatch.setattr(
        event_repo_module, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
    )
    monkeypatch.setattr(
        account_repo_module, "ExchangeAccountRepository", MagicMock(return_value=account_repo)
    )
    monkeypatch.setattr(
        strategy_repo_module, "StrategyRepository", MagicMock(return_value=strategy_repo)
    )
    provider = SimpleNamespace(fetch_ohlcv=AsyncMock(return_value=rows))
    monkeypatch.setattr(celery_module, "get_ccxt_provider_for_worker", lambda: provider)
    captured_kwargs: list[dict[str, Any]] = []

    def fake_run_live(*_args: object, **kwargs: Any) -> LiveSignalResult:
        captured_kwargs.append(kwargs)
        return run_result

    monkeypatch.setattr(event_loop_module, "run_live", fake_run_live)
    monkeypatch.setattr(live_signal_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(live_signal_module, "_reconcile_conditional_entries", AsyncMock())
    monkeypatch.setattr(
        live_signal_module.dispatch_live_signal_event_task, "apply_async", MagicMock()
    )
    monkeypatch.setattr(
        live_signal_module.sweep_conditional_entries_task, "apply_async", MagicMock()
    )
    monkeypatch.setattr(live_signal_module, "send_rule_alert", AsyncMock(return_value={}))
    return sess_repo, event_repo, captured_kwargs


@pytest.mark.asyncio
async def test_strategy_settings_fill_timing_reaches_run_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """전략 설정의 체결 시점이 라이브 인터프리터 호출까지 보존된다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    sess = _session(last_evaluated_bar_time=None)
    _sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0),
        run_result=_result(last_bar_time=t0, signals=[]),
        inserted_events=[],
        fill_timing="next_bar_open",
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["fill_timing"] == "next_bar_open"


def _rows(*times: datetime) -> list[list[object]]:
    return [[int(time.timestamp() * 1000), 1, 2, 0, 1, 100] for time in times]


@pytest.mark.asyncio
async def test_short_gap_catches_up_two_bars_without_duplicate_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1분 결손은 watermark 뒤 두 bar를 한 outbox INSERT로 보낸다."""
    t0 = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    t1, t2 = t0 + timedelta(minutes=1), t0 + timedelta(minutes=2)
    sess = _session(last_evaluated_bar_time=t0)
    signals = [
        LiveSignal("entry", "long", "A", 1.0, 0, bar_time=t1),
        LiveSignal("close", "long", "A", 1.0, 0, bar_time=t2),
    ]
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t1, t2),
        run_result=_result(last_bar_time=t2, signals=signals),
        inserted_events=[_event(signal, sess.id) for signal in signals],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["events_inserted"] == 2
    assert run_kwargs == [
        {
            "initial_capital": 8192.0,
            "live_position_size_pct": 10.0,
            "leverage": 2.0,
            "sessions_allowed": (),
            "pyramiding": None,
            "fill_timing": "bar_close",
            "emit_from_bar_time": t0,
            "position_epoch": t0,
        }
    ]
    payload = event_repo.insert_pending_events.await_args.kwargs["signals"]
    keys = {
        (signal["bar_time"], signal["sequence_no"], signal["action"], signal["trade_id"])
        for signal in payload
    }
    assert len(payload) == len(keys) == 2
    sess_repo.deactivate.assert_not_awaited()


@pytest.mark.asyncio
async def test_long_gap_both_flat_resyncs_without_deactivation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """상한 밖 공백이라도 양쪽 flat이면 마지막 bar만 조용히 이어간다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0)
    sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[{"id": "B", "direction": "long", "entry_bar": 1}],
        ),
        inserted_events=[_event(last_signal, sess.id)],
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert "emit_from_bar_time" not in run_kwargs[0]
    assert run_kwargs[0]["position_epoch"] == t6
    sess_repo.deactivate.assert_not_awaited()
    sess_repo.try_claim_bar.assert_awaited_once_with(sess.id, t6, ANY)


@pytest.mark.asyncio
async def test_long_gap_exchange_flat_realigns_stored_epoch_to_last_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """state 행이 있어도 장기 공백의 실제 flat은 저장 epoch 대신 마지막 bar를 쓴다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    stored_epoch = t0 - timedelta(hours=1)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[{"id": "B", "direction": "long", "entry_bar": 1}],
        ),
        inserted_events=[_event(last_signal, sess.id)],
        previous_state=SimpleNamespace(
            last_strategy_state_report={"_qb_position_epoch": stored_epoch.isoformat()},
            equity_curve=None,
        ),
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["position_epoch"] == t6
    assert run_kwargs[0]["position_epoch"] != stored_epoch
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_gap_keeps_stored_epoch_when_state_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """짧은 공백은 저장된 epoch을 유지해 장기 flat realign과 구분한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=1)
    stored_epoch = t0 - timedelta(hours=1)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0, bar_time=t1)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t1),
        run_result=_result(last_bar_time=t1, signals=[last_signal]),
        inserted_events=[_event(last_signal, sess.id)],
        previous_state=SimpleNamespace(
            last_strategy_state_report={"_qb_position_epoch": stored_epoch.isoformat()},
            equity_curve=None,
        ),
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["position_epoch"] == stored_epoch
    assert run_kwargs[0]["position_epoch"] != t1
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_position_mismatch_deactivates_with_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """상한 밖 공백의 거래소 보유분은 과거 발주 대신 세션 중단으로 표면화한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
    )
    _patch_positions(monkeypatch, positions=[object()])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")
    await asyncio.sleep(0)

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_long_gap_position_fetch_failure_deactivates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """거래소 조회 실패는 flat으로 간주하지 않아 장기 공백을 fail-closed 처리한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(last_bar_time=t6, signals=[]),
        inserted_events=[],
    )
    _patch_positions(monkeypatch, positions=Exception("boom"))

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_called()


@pytest.mark.asyncio
async def test_new_session_never_catches_up_warmup_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """신규 세션은 300 bar warmup에 신호가 있어도 마지막 bar만 발행한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    sess = _session(last_evaluated_bar_time=None)
    last_signal = LiveSignal("entry", "long", "B", 1.0, 0)
    _sess_repo, _event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t0 + timedelta(minutes=1)),
        run_result=_result(last_bar_time=t0 + timedelta(minutes=1), signals=[last_signal]),
        inserted_events=[_event(last_signal, sess.id)],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["events_inserted"] == 1
    assert "emit_from_bar_time" not in run_kwargs[0]


def _patch_positions(
    monkeypatch: pytest.MonkeyPatch, *, positions: list[object] | Exception
) -> None:
    """장기 resync와 dispatch close 가드가 공유하는 거래소 포지션 조회를 대체한다."""
    provider = SimpleNamespace(fetch_open_positions=AsyncMock())
    if isinstance(positions, Exception):
        provider.fetch_open_positions.side_effect = positions
    else:
        provider.fetch_open_positions.return_value = positions

    import src.trading.providers as providers_module
    import src.trading.services.account_service as account_service_module

    monkeypatch.setattr(providers_module, "BybitFuturesProvider", lambda: provider)
    monkeypatch.setattr(
        account_service_module.ExchangeAccountService,
        "get_credentials_for_order",
        AsyncMock(return_value=object()),
    )


def _dispatch_event(*, action: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        session_id=uuid4(),
        bar_time=datetime(2026, 5, 1, 12, tzinfo=UTC),
        sequence_no=0,
        action=action,
        direction="long",
        trade_id="L",
        qty=Decimal("1"),
        comment="",
        status=LiveSignalEventStatus.pending,
        realized_pnl=None,
        take_profit=None,
        stop_loss=None,
        trailing_stop=None,
    )


def _install_dispatch(
    monkeypatch: pytest.MonkeyPatch, *, event: SimpleNamespace
) -> tuple[AsyncMock, list[object]]:
    """dispatch의 DB/service 경계를 fake로 두고 execute 호출만 수집한다."""
    _patch_engine(monkeypatch)
    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_failed = AsyncMock(return_value=1)
    event_repo.mark_dispatched = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()
    sess = _session(last_evaluated_bar_time=None)
    sess.id = event.session_id
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=_strategy(sess.strategy_id))
    calls: list[object] = []

    class OrderServiceSpy:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def execute(self, request: object, **_kwargs: object) -> tuple[SimpleNamespace, bool]:
            calls.append(request)
            return SimpleNamespace(id=uuid4()), False

    import src.strategy.repository as strategy_repo_module
    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.kill_switch_event_repository as kse_repo_module
    import src.trading.repositories.live_signal_event_repository as event_repo_module
    import src.trading.repositories.live_signal_session_repository as sess_repo_module
    import src.trading.repositories.order_repository as order_repo_module
    import src.trading.services.order_service as order_service_module

    monkeypatch.setattr(
        event_repo_module, "LiveSignalEventRepository", MagicMock(return_value=event_repo)
    )
    monkeypatch.setattr(
        sess_repo_module, "LiveSignalSessionRepository", MagicMock(return_value=sess_repo)
    )
    monkeypatch.setattr(
        strategy_repo_module, "StrategyRepository", MagicMock(return_value=strategy_repo)
    )
    monkeypatch.setattr(
        account_repo_module, "ExchangeAccountRepository", MagicMock(return_value=AsyncMock())
    )
    monkeypatch.setattr(
        kse_repo_module, "KillSwitchEventRepository", MagicMock(return_value=AsyncMock())
    )
    monkeypatch.setattr(order_repo_module, "OrderRepository", MagicMock(return_value=AsyncMock()))
    monkeypatch.setattr(order_service_module, "OrderService", OrderServiceSpy)
    return event_repo, calls


@pytest.mark.asyncio
async def test_close_with_explicitly_flat_exchange_is_not_dispatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """close의 0건 응답은 실패 전이하고 OrderService.execute를 호출하지 않는다."""
    event = _dispatch_event(action="close")
    event_repo, calls = _install_dispatch(monkeypatch, event=event)
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._async_dispatch_event(event.id)

    assert result == {"failed": "close_position_flat"}
    assert calls == []
    event_repo.mark_failed.assert_awaited_once_with(event.id, error="close_position_flat")


@pytest.mark.asyncio
async def test_close_position_lookup_failure_is_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """close 포지션 조회 예외는 정당한 청산을 막지 않는다."""
    event = _dispatch_event(action="close")
    _event_repo, calls = _install_dispatch(monkeypatch, event=event)
    _patch_positions(monkeypatch, positions=RuntimeError("exchange down"))

    result = await live_signal_module._async_dispatch_event(event.id)

    assert "dispatched" in result
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_entry_does_not_fetch_positions(monkeypatch: pytest.MonkeyPatch) -> None:
    """진입은 REST 지연을 피하려고 포지션 조회를 절대 열지 않는다."""
    event = _dispatch_event(action="entry")
    _event_repo, calls = _install_dispatch(monkeypatch, event=event)
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._async_dispatch_event(event.id)

    assert "dispatched" in result
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_long_gap_exchange_flat_realigns_epoch_instead_of_deactivating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """거래소 flat 장기 공백은 마지막 bar epoch으로 정렬해 정상 진행한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "B", 1.0, 0)
    sess_repo, event_repo, run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[],
        ),
        inserted_events=[_event(last_signal, sess.id)],
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    assert run_kwargs[0]["position_epoch"] == t6
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_gap_exchange_flat_with_carried_position_still_deactivates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """마지막 bar 이전 entry는 epoch 배선 회귀를 잡기 위해 계속 fail-closed 한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    t6 = t0 + timedelta(minutes=6)
    sess = _session(last_evaluated_bar_time=t0)
    last_signal = LiveSignal("close", "long", "B", 1.0, 0)
    sess_repo, event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0, t6),
        run_result=_result(
            last_bar_time=t6,
            signals=[last_signal],
            open_trades=[{"id": "B", "direction": "long", "entry_bar": 0}],
        ),
        inserted_events=[_event(last_signal, sess.id)],
    )
    _patch_positions(monkeypatch, positions=[])

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result == {"deactivated": "gap_resync_position_mismatch"}
    sess_repo.deactivate.assert_awaited_once()
    event_repo.insert_pending_events.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_upsert_records_position_epoch(monkeypatch: pytest.MonkeyPatch) -> None:
    """성공 평가 state JSONB는 다음 재생이 재사용할 epoch을 보존한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    sess = _session(last_evaluated_bar_time=None)
    sess_repo, _event_repo, _run_kwargs = _install_evaluation(
        monkeypatch,
        sess=sess,
        rows=_rows(t0),
        run_result=_result(last_bar_time=t0, signals=[]),
        inserted_events=[],
    )

    result = await live_signal_module._evaluate_session_inner(sess.id, "1m")

    assert result["evaluated"] is True
    report = sess_repo.upsert_state.await_args.kwargs["last_strategy_state_report"]
    assert report["_qb_position_epoch"] == t0.isoformat()

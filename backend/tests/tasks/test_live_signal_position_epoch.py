"""live signal position epoch 해석과 장기 공백 재정렬을 검증한다."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]

from src.trading.models import (  # noqa: E402
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    LiveSignalInterval,
)


@pytest.mark.parametrize(
    ("previous_report, has_previous_state, realign, session_created_at, last_bar_time, expected"),
    [
        (
            {"_qb_position_epoch": "2026-05-01T11:00:00+00:00"},
            True,
            True,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
        ),
        (
            {"_qb_position_epoch": "2026-05-01T11:00:00+00:00"},
            False,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
        ),
        (
            {"_qb_position_epoch": "2026-05-01T20:00:00+09:00"},
            True,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 11, tzinfo=UTC),
        ),
        (
            {"_qb_position_epoch": "2026-05-01T11:00:00"},
            True,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 11, tzinfo=UTC),
        ),
        (
            {"other": "value"},
            True,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 10, tzinfo=UTC),
        ),
        (
            {},
            True,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 10, tzinfo=UTC),
        ),
        (
            "not-a-report",
            True,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 10, tzinfo=UTC),
        ),
        (
            {"_qb_position_epoch": "2026-05-01T13:00:00+00:00"},
            True,
            False,
            datetime(2026, 5, 1, 10, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
            datetime(2026, 5, 1, 12, tzinfo=UTC),
        ),
        (
            {},
            True,
            False,
            datetime(2026, 5, 1, 10),
            datetime(2026, 5, 1, 12),
            datetime(2026, 5, 1, 10, tzinfo=UTC),
        ),
    ],
)
def test_resolve_position_epoch(
    previous_report: object,
    has_previous_state: bool,
    realign: bool,
    session_created_at: datetime,
    last_bar_time: datetime,
    expected: datetime,
) -> None:
    """epoch 선택표, clamp, naive UTC 정규화를 각각 고정한다."""
    result = live_signal_module._resolve_position_epoch(
        previous_report,
        session_created_at=session_created_at,
        last_bar_time=last_bar_time,
        has_previous_state=has_previous_state,
        realign=realign,
    )

    assert result == expected
    assert result.tzinfo == UTC


def test_resolve_position_epoch_unparsable_value_falls_back_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """손상된 JSONB epoch은 세션 중단 대신 created_at fallback과 경고를 남긴다."""
    created_at = datetime(2026, 5, 1, 10, tzinfo=UTC)
    caplog.set_level(logging.WARNING, logger="src.tasks.live_signal")

    result = live_signal_module._resolve_position_epoch(
        {"_qb_position_epoch": "not-an-iso8601-value"},
        session_created_at=created_at,
        last_bar_time=datetime(2026, 5, 1, 12, tzinfo=UTC),
        has_previous_state=True,
        realign=False,
    )

    assert result == created_at
    assert "live_signal_position_epoch_unparsable" in caplog.messages


class _SessionContext:
    """실제 엔진을 제외한 평가 경계를 메모리 mock으로 고정한다."""

    def __init__(self, session: AsyncMock) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncMock:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = AsyncMock()
    engine.dispose = AsyncMock()
    session = AsyncMock()
    monkeypatch.setattr(
        live_signal_module,
        "create_worker_engine_and_sm",
        lambda: (engine, lambda: _SessionContext(session)),
    )


def _patch_flat_positions(monkeypatch: pytest.MonkeyPatch) -> None:
    """gap resync 및 발산 관측의 거래소 조회는 모두 실제 flat을 반환한다."""
    provider = SimpleNamespace(fetch_open_positions=AsyncMock(return_value=[]))

    import src.trading.providers as providers_module
    import src.trading.services.account_service as account_service_module

    monkeypatch.setattr(providers_module, "BybitFuturesProvider", lambda: provider)
    monkeypatch.setattr(
        account_service_module.ExchangeAccountService,
        "get_credentials_for_order",
        AsyncMock(return_value=object()),
    )


def _install_actual_engine_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    start: datetime,
    last_evaluated_bar_time: datetime,
    previous_state: object | None = None,
) -> tuple[SimpleNamespace, AsyncMock, AsyncMock, list[dict[str, Any]]]:
    """실제 run_live를 감싸 task 호출 인자와 원장 조회만 관찰한다."""
    rows = [
        [int((start + timedelta(minutes=index + 1)).timestamp() * 1000), *values]
        for index, values in enumerate(
            [
                (100.0, 101.0, 99.0, 100.0, 100.0),
                (100.0, 101.0, 98.0, 99.0, 100.0),
                (99.0, 100.0, 97.0, 98.0, 100.0),
                (98.0, 99.0, 96.0, 97.0, 100.0),
                (97.0, 100.0, 96.0, 99.0, 100.0),
                (99.0, 101.0, 98.0, 100.0, 100.0),
            ]
        )
    ]
    session_obj = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=True,
        created_at=start,
        last_evaluated_bar_time=last_evaluated_bar_time,
        equity_baseline_usdt=Decimal("8192"),
    )
    strategy = SimpleNamespace(
        settings={"leverage": 2, "margin_mode": "cross", "position_size_pct": 10.0},
        pine_source=(
            '//@version=5\nstrategy("buy on green")\n'
            'if close > open\n    strategy.entry("L", strategy.long, qty=1.0)\n'
        ),
        trading_sessions=[],
    )
    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=session_obj)
    sess_repo.get_state = AsyncMock(return_value=previous_state)
    sess_repo.try_claim_bar = AsyncMock(return_value=True)
    sess_repo.deactivate = AsyncMock(return_value=1)
    sess_repo.upsert_state = AsyncMock()
    sess_repo.commit = AsyncMock()
    event = SimpleNamespace(
        id=uuid4(),
        bar_time=start + timedelta(minutes=6),
        sequence_no=0,
        action="entry",
        trade_id="L",
        status=LiveSignalEventStatus.pending,
    )
    event_repo = AsyncMock()
    event_repo.sum_realized_pnl_before = AsyncMock(return_value=(Decimal("0"), 0))
    event_repo.sum_realized_pnl_all = AsyncMock(return_value=(Decimal("0"), 0))
    event_repo.list_by_session = AsyncMock(return_value=[])
    event_repo.insert_pending_events = AsyncMock(return_value=[event])
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    )
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)
    _patch_engine(monkeypatch)
    _patch_flat_positions(monkeypatch)

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
    monkeypatch.setattr(live_signal_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(live_signal_module, "_reconcile_conditional_entries", AsyncMock())
    monkeypatch.setattr(
        live_signal_module.dispatch_live_signal_event_task, "apply_async", MagicMock()
    )

    import src.strategy.pine_v2.event_loop as event_loop_module

    real_run_live = event_loop_module.run_live
    captured_kwargs: list[dict[str, Any]] = []

    def capture_run_live(*args: object, **kwargs: Any) -> Any:
        captured_kwargs.append(kwargs)
        return real_run_live(*args, **kwargs)

    monkeypatch.setattr(event_loop_module, "run_live", capture_run_live)

    return session_obj, sess_repo, event_repo, captured_kwargs


@pytest.mark.asyncio
async def test_short_catchup_clamps_position_epoch_before_actual_run_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """state 행 없는 짧은 catch-up은 발행 watermark보다 뒤 epoch을 엔진에 넘기지 않는다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    emit_from_bar_time = t0 + timedelta(minutes=3)
    session_obj, sess_repo, event_repo, run_kwargs = _install_actual_engine_evaluation(
        monkeypatch,
        start=t0,
        last_evaluated_bar_time=emit_from_bar_time,
    )

    result = await live_signal_module._evaluate_session_inner(session_obj.id, "1m")

    assert result["evaluated"] is True
    sess_repo.deactivate.assert_not_awaited()
    event_repo.insert_pending_events.assert_awaited_once()
    assert run_kwargs[0]["emit_from_bar_time"] == emit_from_bar_time
    assert run_kwargs[0]["position_epoch"] == emit_from_bar_time


@pytest.mark.asyncio
async def test_long_gap_resync_uses_epoch_carry_for_actual_run_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """재정렬 epoch까지의 창 안 실현손익을 엔진 사이징 자본에 반영한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    session_obj, sess_repo, event_repo, run_kwargs = _install_actual_engine_evaluation(
        monkeypatch,
        start=t0,
        last_evaluated_bar_time=t0,
    )
    event_repo.sum_realized_pnl_before.side_effect = [
        (Decimal("0"), 0),
        (Decimal("100"), 1),
    ]

    result = await live_signal_module._evaluate_session_inner(session_obj.id, "1m")

    assert result["evaluated"] is True
    sess_repo.deactivate.assert_not_awaited()
    assert [
        call.kwargs["bar_time"] for call in event_repo.sum_realized_pnl_before.await_args_list
    ] == [t0 + timedelta(minutes=1), t0 + timedelta(minutes=6)]
    assert run_kwargs[0]["initial_capital"] == 8292.0


@pytest.mark.asyncio
async def test_short_gap_without_realign_uses_window_carry_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """재정렬이 아닌 짧은 공백은 window_start 기준 carry 조회를 한 번만 한다."""
    t0 = datetime(2026, 5, 1, 12, tzinfo=UTC)
    session_obj, sess_repo, event_repo, run_kwargs = _install_actual_engine_evaluation(
        monkeypatch,
        start=t0,
        last_evaluated_bar_time=t0 + timedelta(minutes=3),
        previous_state=SimpleNamespace(
            last_strategy_state_report={"_qb_position_epoch": t0.isoformat()},
            equity_curve=None,
        ),
    )

    result = await live_signal_module._evaluate_session_inner(session_obj.id, "1m")

    assert result["evaluated"] is True
    sess_repo.deactivate.assert_not_awaited()
    event_repo.sum_realized_pnl_before.assert_awaited_once_with(
        session_obj.id, bar_time=t0 + timedelta(minutes=1)
    )
    assert run_kwargs[0]["initial_capital"] == 8192.0

"""라이브 신호 세션·이벤트 저장소의 실제 DB 계약을 고정한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    LiveSignalInterval,
    LiveSignalSession,
    SessionDeactivationReason,
)
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository


async def _seed_account(db_session: AsyncSession, user: User) -> ExchangeAccount:
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _seed_session(
    db_session: AsyncSession,
    *,
    user: User,
    strategy: Strategy,
    account: ExchangeAccount,
    symbol: str,
    is_active: bool = True,
    deactivated_at: datetime | None = None,
) -> LiveSignalSession:
    live_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=symbol,
        interval=LiveSignalInterval.m5,
        is_active=is_active,
        deactivated_at=deactivated_at,
        deactivated_reason=(SessionDeactivationReason.user_stopped if not is_active else None),
    )
    db_session.add(live_session)
    await db_session.flush()
    return live_session


@pytest.mark.asyncio
async def test_insert_pending_events_is_idempotent_and_keeps_signal_bar_times(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """같은 신호 재생은 중복 없이, 신호별 bar_time·Decimal 레벨은 보존한다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    fallback_bar_time = datetime(2026, 8, 22, 9, tzinfo=UTC)
    earlier_bar_time = fallback_bar_time - timedelta(minutes=5)
    signals = [
        {
            "sequence_no": 1,
            "action": "entry",
            "direction": "long",
            "trade_id": "entry-1",
            "qty": "1.25",
            "comment": "open",
            "take_profit": "110.5",
            "stop_loss": "99.5",
            "trailing_stop": "2.5",
            "bar_time": earlier_bar_time,
        },
        {
            "sequence_no": 2,
            "action": "close",
            "direction": "long",
            "trade_id": "close-1",
            "qty": "1.25",
            "realized_pnl": "3.75",
        },
    ]

    inserted = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=fallback_bar_time,
        signals=signals,
    )
    repeated = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=fallback_bar_time,
        signals=signals,
    )

    assert [event.id for event in repeated] == [event.id for event in inserted]
    by_trade_id = {event.trade_id: event for event in inserted}
    assert by_trade_id["entry-1"].bar_time == earlier_bar_time
    assert by_trade_id["entry-1"].qty == Decimal("1.25")
    assert by_trade_id["entry-1"].take_profit == Decimal("110.5")
    assert by_trade_id["entry-1"].stop_loss == Decimal("99.5")
    assert by_trade_id["entry-1"].trailing_stop == Decimal("2.5")
    assert by_trade_id["close-1"].bar_time == fallback_bar_time
    assert by_trade_id["close-1"].realized_pnl == Decimal("3.75")


@pytest.mark.asyncio
async def test_event_repository_handles_empty_input_and_pending_failure_transition(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """빈 신호는 쓰지 않고, pending 이벤트만 실패 상태로 한 번 전이한다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ETHUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    bar_time = datetime(2026, 8, 22, 10, tzinfo=UTC)

    assert (
        await repository.insert_pending_events(
            session_id=live_session.id,
            bar_time=bar_time,
            signals=[],
        )
        == []
    )
    [pending] = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=bar_time,
        signals=[
            {
                "sequence_no": 1,
                "action": "entry",
                "direction": "short",
                "trade_id": "failure-1",
                "qty": "2",
            }
        ],
    )

    assert [event.id for event in await repository.list_pending()] == [pending.id]
    assert await repository.mark_failed(pending.id, error="x" * 2101) == 1
    assert await repository.mark_failed(pending.id, error="second attempt") == 0

    stored = await repository.get_by_id(pending.id)
    assert stored is not None
    assert stored.status == LiveSignalEventStatus.failed
    assert stored.retry_count == 1
    assert stored.error_message == "x" * 2000
    assert await repository.list_pending() == []


@pytest.mark.asyncio
async def test_try_claim_bar_only_accepts_a_newer_bar_for_an_active_session(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """동일·과거 bar의 두 번째 worker는 claim winner가 될 수 없다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="SOLUSDT",
    )
    repository = LiveSignalSessionRepository(db_session)
    bar_time = datetime(2026, 8, 22, 11, tzinfo=UTC)
    claim_token = uuid4()

    assert await repository.try_claim_bar(live_session.id, bar_time, claim_token) is True
    assert await repository.try_claim_bar(live_session.id, bar_time, uuid4()) is False
    assert (
        await repository.try_claim_bar(
            live_session.id,
            bar_time - timedelta(minutes=5),
            uuid4(),
        )
        is False
    )

    await db_session.refresh(live_session)
    assert live_session.last_evaluated_bar_time == bar_time
    assert live_session.bar_claim_token == claim_token


@pytest.mark.asyncio
async def test_session_repository_lists_inactive_rows_and_upserts_state(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """최근 종료 목록의 limit과 1:1 상태 갱신의 기존 equity curve 보존을 검증한다."""
    account = await _seed_account(db_session, user)
    earlier = datetime(2026, 8, 22, 8, tzinfo=UTC)
    older = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="XRPUSDT",
        is_active=False,
        deactivated_at=earlier,
    )
    newer = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ADAUSDT",
        is_active=False,
        deactivated_at=earlier + timedelta(minutes=1),
    )
    active = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="DOGEUSDT",
    )
    repository = LiveSignalSessionRepository(db_session)

    assert await repository.list_recent_inactive_by_user(user.id, limit=0) == []
    assert [row.id for row in await repository.list_recent_inactive_by_user(user.id, limit=1)] == [
        newer.id
    ]
    assert (
        await repository.deactivate_all_by_owner(
            user.id,
            at=earlier + timedelta(minutes=2),
            reason=SessionDeactivationReason.user_stopped,
        )
        == 1
    )
    await db_session.refresh(active)
    assert active.is_active is False

    created = await repository.upsert_state(
        session_id=older.id,
        last_strategy_state_report={"bar": 1},
        total_closed_trades=2,
        total_realized_pnl=Decimal("4.50"),
        equity_curve=[{"timestamp_ms": 1, "cumulative_pnl": "4.50"}],
    )
    updated = await repository.upsert_state(
        session_id=older.id,
        last_strategy_state_report={"bar": 2},
        total_closed_trades=3,
        total_realized_pnl=Decimal("5.25"),
    )

    assert updated is created
    assert updated.last_strategy_state_report == {"bar": 2}
    assert updated.total_closed_trades == 3
    assert updated.total_realized_pnl == Decimal("5.25")
    assert updated.equity_curve == [{"timestamp_ms": 1, "cumulative_pnl": "4.50"}]

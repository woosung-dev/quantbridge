"""ParityRepository의 읽기 전용 세 집합과 원장 조인을 실 DB로 고정한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeExit,
    ExchangeMode,
    ExchangeName,
    ExitAttribution,
    ExitClassification,
    LiveSignalEvent,
    LiveSignalEventStatus,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.outcome_parity import ParityBuckets, ParityObservation
from src.trading.repositories.order_repository import SessionScope
from src.trading.repositories.parity_repository import ParityRepository

_BASE = datetime(2026, 7, 28, 12, tzinfo=UTC)
_BTC = "BTC/USDT"
_BTC_RAW = "BTCUSDT"


@dataclass(frozen=True, slots=True)
class _Seed:
    strategy: Strategy
    account: ExchangeAccount
    other_account: ExchangeAccount
    session: LiveSignalSession
    scope: SessionScope


async def _seed(
    db_session: AsyncSession,
    *,
    deactivated_at: datetime | None = None,
) -> _Seed:
    user = User(
        clerk_user_id=f"parity-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    strategy = Strategy(
        user_id=user.id,
        name="Parity strategy",
        pine_source="//@version=5\nstrategy('parity')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    other_account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"other-key",
        api_secret_encrypted=b"other-secret",
    )
    db_session.add_all([user, strategy, account, other_account])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=_BTC,
        interval=LiveSignalInterval.m1,
        is_active=deactivated_at is None,
        created_at=_BASE,
        deactivated_at=deactivated_at,
    )
    db_session.add(session)
    await db_session.flush()
    return _Seed(
        strategy=strategy,
        account=account,
        other_account=other_account,
        session=session,
        scope=SessionScope.from_live_session(session),
    )


async def _order(
    db_session: AsyncSession,
    seed: _Seed,
    *,
    realized_pnl: str | None,
    synced: bool,
    filled_at: datetime | None = None,
    state: OrderState = OrderState.filled,
) -> Order:
    order = Order(
        strategy_id=seed.strategy.id,
        exchange_account_id=seed.account.id,
        symbol=_BTC,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1"),
        state=state,
        realized_pnl=Decimal(realized_pnl) if realized_pnl is not None else None,
        realized_pnl_synced_at=_BASE + timedelta(minutes=30) if synced else None,
        filled_at=filled_at or (_BASE + timedelta(minutes=1)),
    )
    db_session.add(order)
    await db_session.flush()
    return order


async def _close_event(
    db_session: AsyncSession,
    seed: _Seed,
    *,
    sequence_no: int,
    realized_pnl: str | None,
    order_id: UUID | None = None,
    status: LiveSignalEventStatus = LiveSignalEventStatus.dispatched,
    action: str = "close",
) -> LiveSignalEvent:
    event = LiveSignalEvent(
        session_id=seed.session.id,
        bar_time=_BASE + timedelta(seconds=sequence_no),
        sequence_no=sequence_no,
        action=action,
        direction="long",
        trade_id=f"close-{sequence_no}-{uuid4().hex}",
        qty=Decimal("1"),
        realized_pnl=Decimal(realized_pnl) if realized_pnl is not None else None,
        status=status,
        order_id=order_id,
    )
    db_session.add(event)
    await db_session.flush()
    return event


async def _exchange_exit(
    db_session: AsyncSession,
    seed: _Seed,
    *,
    matched_order_id: UUID | None = None,
    order_link_id: str | None = None,
    account: ExchangeAccount | None = None,
    symbol: str = _BTC_RAW,
    side: str = "Sell",
    closed_size: str | None = "1",
    avg_entry_price: str | None = "100",
    avg_exit_price: str | None = "110",
    classification: ExitClassification = ExitClassification.ours,
) -> ExchangeExit:
    exchange_exit = ExchangeExit(
        exchange_account_id=(account or seed.account).id,
        exchange_order_id=f"exit-{uuid4().hex}",
        row_hash=uuid4().hex,
        symbol=symbol,
        side=side,
        closed_pnl=Decimal("-1"),
        closed_size=Decimal(closed_size) if closed_size is not None else None,
        avg_entry_price=Decimal(avg_entry_price) if avg_entry_price is not None else None,
        avg_exit_price=Decimal(avg_exit_price) if avg_exit_price is not None else None,
        exchange_created_at=_BASE,
        classification=classification,
        order_link_id=order_link_id,
        matched_order_id=matched_order_id,
        attribution_confidence=ExitAttribution.none,
        raw={"source": "parity-repository-test"},
    )
    db_session.add(exchange_exit)
    await db_session.flush()
    return exchange_exit


@pytest.mark.asyncio
async def test_load_parity_inputs_uses_only_synced_orders_as_actuals(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    confirmed = await _order(db_session, seed, realized_pnl="-4", synced=True)
    unsynced = await _order(db_session, seed, realized_pnl="99", synced=False)
    await _order(db_session, seed, realized_pnl="8", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="-1", order_id=confirmed.id)
    await _close_event(db_session, seed, sequence_no=2, realized_pnl="-2", order_id=confirmed.id)
    await _close_event(db_session, seed, sequence_no=3, realized_pnl="99", order_id=unsynced.id)

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == [
        ParityObservation(
            expected_gross=Decimal("-3"),
            actual_net=Decimal("-4"),
            actual_gross=None,
            round_trip_notional=None,
        )
    ]
    assert buckets == ParityBuckets(
        expected_only_count=1,
        expected_only_gross=Decimal("99"),
        actual_only_count=1,
        actual_only_net=Decimal("8"),
        unattributed_count=0,
    )


@pytest.mark.asyncio
async def test_entry_events_are_excluded_from_the_expected_axis(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    order = await _order(db_session, seed, realized_pnl="2", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="1", order_id=order.id)
    await _close_event(
        db_session,
        seed,
        sequence_no=2,
        realized_pnl="99",
        action="entry",
    )

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert len(observations) == 1
    assert observations[0].expected_gross == Decimal("1")
    assert buckets.expected_only_count == 0
    assert buckets.expected_only_gross == Decimal("0")


@pytest.mark.asyncio
async def test_load_parity_inputs_keeps_ledger_rows_in_the_order_account(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    order = await _order(db_session, seed, realized_pnl="7", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="6", order_id=order.id)
    await _exchange_exit(db_session, seed, matched_order_id=order.id)
    await _exchange_exit(
        db_session,
        seed,
        account=seed.other_account,
        matched_order_id=order.id,
    )

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == [
        ParityObservation(
            expected_gross=Decimal("6"),
            actual_net=Decimal("7"),
            actual_gross=Decimal("10"),
            round_trip_notional=Decimal("210"),
        )
    ]
    assert buckets.unattributed_count == 0


@pytest.mark.asyncio
async def test_load_parity_inputs_recovers_link_id_without_casting_malformed_links(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    order = await _order(db_session, seed, realized_pnl="1", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="2", order_id=order.id)
    await _exchange_exit(db_session, seed, order_link_id=str(order.id))
    await _exchange_exit(db_session, seed, order_link_id="not-a-uuid")

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations[0].actual_gross == Decimal("10")
    assert observations[0].round_trip_notional == Decimal("210")
    assert buckets.unattributed_count == 1


@pytest.mark.asyncio
async def test_load_parity_inputs_fails_closed_for_multiple_ledger_rows(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    order = await _order(db_session, seed, realized_pnl="-4", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="-3", order_id=order.id)
    await _exchange_exit(db_session, seed, matched_order_id=order.id)
    await _exchange_exit(db_session, seed, matched_order_id=order.id)

    observations, _ = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == [
        ParityObservation(
            expected_gross=Decimal("-3"),
            actual_net=Decimal("-4"),
            actual_gross=None,
            round_trip_notional=None,
        )
    ]


@pytest.mark.asyncio
async def test_load_parity_inputs_fails_closed_for_null_ledger_evaluation_field(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    order = await _order(db_session, seed, realized_pnl="3", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="2", order_id=order.id)
    await _exchange_exit(db_session, seed, matched_order_id=order.id, avg_entry_price=None)

    observations, _ = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations[0].actual_gross is None
    assert observations[0].round_trip_notional is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("side", "expected_gross"),
    [("Buy", Decimal("-10")), ("Sell", Decimal("10"))],
)
async def test_load_parity_inputs_uses_exchange_exit_side_for_gross_sign(
    db_session: AsyncSession,
    side: str,
    expected_gross: Decimal,
) -> None:
    seed = await _seed(db_session)
    order = await _order(db_session, seed, realized_pnl="1", synced=True)
    await _close_event(db_session, seed, sequence_no=1, realized_pnl="1", order_id=order.id)
    await _exchange_exit(db_session, seed, matched_order_id=order.id, side=side)

    observations, _ = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations[0].actual_gross == expected_gross


@pytest.mark.asyncio
async def test_load_parity_inputs_counts_raw_symbol_unattributed_exit(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    await _exchange_exit(db_session, seed)

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == []
    assert buckets.unattributed_count == 1


@pytest.mark.asyncio
async def test_load_parity_inputs_excludes_order_at_session_end_boundary(
    db_session: AsyncSession,
) -> None:
    deactivated_at = _BASE + timedelta(hours=1)
    seed = await _seed(db_session, deactivated_at=deactivated_at)
    await _order(
        db_session,
        seed,
        realized_pnl="5",
        synced=True,
        filled_at=deactivated_at,
    )

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == []
    assert buckets.actual_only_count == 0
    assert buckets.actual_only_net == Decimal("0")


@pytest.mark.asyncio
async def test_load_parity_inputs_scopes_events_by_session_id_not_order_scope(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    rejected = await _order(
        db_session,
        seed,
        realized_pnl="3",
        synced=False,
        state=OrderState.rejected,
    )
    await _close_event(
        db_session,
        seed,
        sequence_no=1,
        realized_pnl="4",
        status=LiveSignalEventStatus.failed,
    )
    await _close_event(
        db_session,
        seed,
        sequence_no=2,
        realized_pnl="3",
        order_id=rejected.id,
    )
    await _close_event(
        db_session,
        seed,
        sequence_no=3,
        realized_pnl=None,
        status=LiveSignalEventStatus.failed,
    )

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == []
    assert buckets.expected_only_count == 3
    assert buckets.expected_only_gross == Decimal("7")


@pytest.mark.asyncio
async def test_load_parity_inputs_keeps_unmatched_bracket_exit_out_of_money_totals(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    await _exchange_exit(
        db_session,
        seed,
        classification=ExitClassification.bracket_tp,
    )

    observations, buckets = await ParityRepository(db_session).load_parity_inputs(
        session_ids=[seed.session.id], scopes=[seed.scope]
    )

    assert observations == []
    assert buckets == ParityBuckets(
        expected_only_count=0,
        expected_only_gross=Decimal("0"),
        actual_only_count=0,
        actual_only_net=Decimal("0"),
        unattributed_count=1,
    )

# 라이브 신호 이벤트 carry 집계의 실DB 창 경계를 검증한다.

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEvent,
    LiveSignalEventStatus,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository


@pytest.mark.asyncio
async def test_realized_pnl_sums_are_session_scoped_and_all_ignores_bar_time(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """carry는 창 경계를 지키고 화면 원장 합계는 모든 같은 세션 close를 센다."""
    window_start = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add(account)
    await db_session.flush()
    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    other_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="ETH/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add_all([session, other_session])
    await db_session.flush()
    db_session.add_all(
        [
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start - timedelta(minutes=1),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="before",
                qty=Decimal("1"),
                realized_pnl=Decimal("1.25"),
                status=LiveSignalEventStatus.failed,
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start,
                sequence_no=2,
                action="close",
                direction="long",
                trade_id="at-boundary",
                qty=Decimal("1"),
                realized_pnl=Decimal("9.99"),
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start + timedelta(minutes=1),
                sequence_no=3,
                action="close",
                direction="long",
                trade_id="after",
                qty=Decimal("1"),
                realized_pnl=Decimal("3.50"),
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start - timedelta(minutes=2),
                sequence_no=4,
                action="entry",
                direction="long",
                trade_id="entry-null-pnl",
                qty=Decimal("1"),
            ),
            LiveSignalEvent(
                session_id=other_session.id,
                bar_time=window_start - timedelta(minutes=1),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="other-session",
                qty=Decimal("1"),
                realized_pnl=Decimal("99.99"),
            ),
        ]
    )
    await db_session.flush()

    repository = LiveSignalEventRepository(db_session)
    total_pnl, closed_count = await repository.sum_realized_pnl_before(
        session.id, bar_time=window_start
    )
    all_total_pnl, all_closed_count = await repository.sum_realized_pnl_all(session.id)

    assert total_pnl == Decimal("1.25")
    assert closed_count == 1
    assert all_total_pnl == Decimal("14.74")
    assert all_closed_count == 3


@pytest.mark.asyncio
async def test_list_events_returns_order_state_with_one_joined_order_query(
    client, mock_authed_user, db_session: AsyncSession
) -> None:
    """이벤트 상태와 주문 결과를 함께 반환하고 주문별 추가 조회를 만들지 않는다."""
    user = mock_authed_user
    strategy = Strategy(
        user_id=user.id,
        name="event-order-state",
        pine_source="//",
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
    db_session.add_all([strategy, account])
    await db_session.flush()
    live_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add(live_session)
    await db_session.flush()

    rejected_order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1"),
        state=OrderState.rejected,
    )
    filled_order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1"),
        state=OrderState.filled,
    )
    db_session.add_all([rejected_order, filled_order])
    await db_session.flush()
    db_session.add_all(
        [
            LiveSignalEvent(
                session_id=live_session.id,
                bar_time=datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="rejected",
                qty=Decimal("1"),
                status=LiveSignalEventStatus.dispatched,
                order_id=rejected_order.id,
            ),
            LiveSignalEvent(
                session_id=live_session.id,
                bar_time=datetime(2026, 7, 30, 12, 1, tzinfo=UTC),
                sequence_no=2,
                action="close",
                direction="long",
                trade_id="filled",
                qty=Decimal("1"),
                status=LiveSignalEventStatus.dispatched,
                order_id=filled_order.id,
            ),
            LiveSignalEvent(
                session_id=live_session.id,
                bar_time=datetime(2026, 7, 30, 12, 2, tzinfo=UTC),
                sequence_no=3,
                action="close",
                direction="long",
                trade_id="unlinked",
                qty=Decimal("1"),
                status=LiveSignalEventStatus.dispatched,
            ),
        ]
    )
    await db_session.commit()

    order_queries: list[str] = []
    connection = db_session.sync_session.bind

    def capture_order_query(conn, cursor, statement, parameters, context, executemany) -> None:
        if "trading.orders" in statement:
            order_queries.append(statement)

    event.listen(connection, "before_cursor_execute", capture_order_query)
    try:
        response = await client.get(f"/api/v1/live-sessions/{live_session.id}/events")
    finally:
        event.remove(connection, "before_cursor_execute", capture_order_query)

    assert response.status_code == 200, response.text
    items_by_trade_id = {item["trade_id"]: item for item in response.json()["items"]}
    assert items_by_trade_id["rejected"]["order_state"] == "rejected"
    assert items_by_trade_id["filled"]["order_state"] == "filled"
    assert items_by_trade_id["unlinked"]["order_state"] is None
    assert len(order_queries) == 1

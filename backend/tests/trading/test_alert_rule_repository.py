# 세션 귀속 이벤트만 손실 규칙 손익 합계에 반영되는지 검증한다

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEvent,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.order_repository import OrderRepository


@pytest.mark.asyncio
async def test_sum_filled_realized_pnl_uses_only_orders_attributed_to_session(
    db_session: AsyncSession,
) -> None:
    user = User(
        clerk_user_id=f"alert-rule-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()
    strategy = Strategy(
        user_id=user.id,
        name="alert rule scope",
        pine_source="//@version=5\nstrategy('scope')",
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
    target_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
    )
    other_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="ETHUSDT",
        interval=LiveSignalInterval.m5,
    )
    db_session.add_all([target_session, other_session])
    await db_session.flush()

    def order(*, state: OrderState, pnl: str) -> Order:
        return Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=state,
            realized_pnl=Decimal(pnl),
        )

    attributed = order(state=OrderState.filled, pnl="-5")
    other_session_order = order(state=OrderState.filled, pnl="-7")
    unattributed = order(state=OrderState.filled, pnl="99")
    unfilled = order(state=OrderState.submitted, pnl="-13")
    db_session.add_all([attributed, other_session_order, unattributed, unfilled])
    await db_session.flush()
    now = datetime.now(UTC)
    db_session.add_all(
        [
            LiveSignalEvent(
                session_id=target_session.id,
                bar_time=now,
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="target",
                qty=Decimal("1"),
                order_id=attributed.id,
            ),
            LiveSignalEvent(
                session_id=target_session.id,
                bar_time=now + timedelta(minutes=5),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="unfilled",
                qty=Decimal("1"),
                order_id=unfilled.id,
            ),
            LiveSignalEvent(
                session_id=other_session.id,
                bar_time=now,
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="other",
                qty=Decimal("1"),
                order_id=other_session_order.id,
            ),
        ]
    )
    await db_session.flush()

    assert await OrderRepository(db_session).sum_filled_realized_pnl_for_live_session(
        target_session.id
    ) == Decimal("-5")

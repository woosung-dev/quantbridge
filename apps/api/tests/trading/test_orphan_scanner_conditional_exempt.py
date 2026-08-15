# 조건부 진입 주문이 orphan scanner 대상에서 제외되는지를 검증한다.

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
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


@pytest.fixture
async def submitted_order_factory(db_session: AsyncSession):
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@s.local",
    )
    strategy = Strategy(
        user_id=user.id,
        name="conditional-exempt",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
        label="conditional-exempt",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(strategy)
    await db_session.flush()
    db_session.add(account)
    await db_session.flush()

    async def _make(*, trigger_price: Decimal | None, exchange_order_id: str | None) -> Order:
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            state=OrderState.submitted,
            trigger_price=trigger_price,
            submitted_at=datetime.now(UTC) - timedelta(hours=1),
            exchange_order_id=exchange_order_id,
        )
        db_session.add(order)
        await db_session.flush()
        return order

    return _make


@pytest.mark.asyncio
async def test_stuck_scanners_exempt_resting_conditional_entries(
    db_session: AsyncSession, submitted_order_factory
) -> None:
    """30분 초과 조건부 진입만 두 stuck 조회에서 제외한다."""
    from src.trading.repositories.order_repository import OrderRepository

    submitted_conditional = await submitted_order_factory(
        trigger_price=Decimal("100"), exchange_order_id="conditional-submitted"
    )
    submitted_market = await submitted_order_factory(
        trigger_price=None, exchange_order_id="market-submitted"
    )
    interrupted_conditional = await submitted_order_factory(
        trigger_price=Decimal("100"), exchange_order_id=None
    )
    interrupted_market = await submitted_order_factory(trigger_price=None, exchange_order_id=None)
    await db_session.commit()

    repo = OrderRepository(db_session)
    cutoff = datetime.now(UTC) - timedelta(minutes=30)
    submitted_ids = {order.id for order in await repo.list_stuck_submitted(cutoff)}
    interrupted_ids = {order.id for order in await repo.list_stuck_submission_interrupted(cutoff)}

    assert submitted_conditional.id not in submitted_ids
    assert submitted_market.id in submitted_ids
    assert interrupted_conditional.id not in interrupted_ids
    assert interrupted_market.id in interrupted_ids

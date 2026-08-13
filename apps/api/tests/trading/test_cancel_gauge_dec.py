"""POST /orders/{id}/cancel — qb_active_orders gauge decrement 검증 (Sprint 9 Phase D FIX-D1).

Opus 지적: router.cancel_order 가 cancelled 로 전이 시 gauge dec 를 호출하지 않아
사용자가 주문 취소할 때마다 qb_active_orders 가 영구적으로 +1 drift 하는 버그.

service.execute 에서 +1 (pending 생성) → router.cancel_order 에서 -1 (cancelled 전이 성공).
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_cancel_decrements_active_orders_gauge(
    client, mock_clerk_auth, db_session
):
    """cancel 성공 (rowcount > 0) 시 qb_active_orders.dec() 호출됨을 delta 로 검증."""
    from decimal import Decimal

    from src.common.metrics import qb_active_orders
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

    user = mock_clerk_auth

    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="s",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    # pending order 하나 준비 (service.execute 경로는 gauge 에 직접 영향 없이,
    # 이 테스트는 cancel path 의 dec 호출만 격리 검증).
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=acc.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.pending,
    )
    db_session.add(order)
    await db_session.commit()

    before = qb_active_orders._value.get()

    resp = await client.post(f"/api/v1/orders/{order.id}/cancel")
    assert resp.status_code == 200, resp.text

    after = qb_active_orders._value.get()
    assert after == before - 1, (
        f"qb_active_orders gauge must decrement by 1 on successful cancel. "
        f"before={before}, after={after}"
    )


@pytest.mark.asyncio
async def test_cancel_on_non_cancellable_state_does_not_decrement_gauge(
    client, mock_clerk_auth, db_session
):
    """이미 filled 상태인 주문 cancel 시도 → 409 + gauge 유지 (dec 호출 금지)."""
    from decimal import Decimal

    from src.common.metrics import qb_active_orders
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

    user = mock_clerk_auth

    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="s2",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=acc.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.filled,  # terminal → cannot cancel
    )
    db_session.add(order)
    await db_session.commit()

    before = qb_active_orders._value.get()

    resp = await client.post(f"/api/v1/orders/{order.id}/cancel")
    assert resp.status_code == 409, resp.text

    after = qb_active_orders._value.get()
    assert after == before, (
        f"qb_active_orders gauge must NOT change when cancel fails (rowcount=0). "
        f"before={before}, after={after}"
    )

"""Orders REST endpoints E2E (T20).

Uses mock_clerk_auth fixture from conftest.py for auth bypass.
URLs: /api/v1/orders (router has no prefix; main.py adds /api/v1).
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_orders_returns_user_only(
    client, mock_clerk_auth, db_session
):
    """GET /api/v1/orders returns only orders belonging to the authed user."""
    from decimal import Decimal

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

    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=acc.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.01"),
            state=OrderState.pending,
        )
    )
    await db_session.commit()

    resp = await client.get("/api/v1/orders?limit=10&offset=0")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BTC/USDT"


@pytest.mark.asyncio
async def test_get_order_by_id_404_if_not_owner(client, mock_clerk_auth):
    """GET /api/v1/orders/{order_id} returns 404 for non-existent order."""
    from uuid import uuid4

    resp = await client.get(f"/api/v1/orders/{uuid4()}")
    assert resp.status_code == 404


def test_order_request_accepts_futures_fields():
    """Sprint 7a T1 — OrderRequest가 leverage/margin_mode를 수용."""
    from decimal import Decimal
    from uuid import uuid4

    from src.trading.models import OrderSide, OrderType
    from src.trading.schemas import OrderRequest

    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    assert req.leverage == 5
    assert req.margin_mode == "cross"


def test_order_request_defaults_to_none_for_spot():
    """Sprint 7a T1 — Spot 경로(futures 필드 미지정) 시 기본값 None."""
    from decimal import Decimal
    from uuid import uuid4

    from src.trading.models import OrderSide, OrderType
    from src.trading.schemas import OrderRequest

    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
    )
    assert req.leverage is None
    assert req.margin_mode is None

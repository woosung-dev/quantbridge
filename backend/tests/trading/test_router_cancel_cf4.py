"""CF4 — POST /orders/{id}/cancel 라우팅.

- submitted(거래소 live) 주문: 202 + cancel_order_task 위임, DB 즉시 flip 안 함 (orphan 방지).
- pending(거래소 미발주) 주문: 200 + 즉시 DB cancel (기존 동작).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

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


async def _setup(db_session, user, *, state: OrderState, exchange_order_id=None):
    acc = ExchangeAccount(
        user_id=user.id, exchange=ExchangeName.bybit, mode=ExchangeMode.demo,
        api_key_encrypted=b"k", api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    strat = Strategy(
        user_id=user.id, name="cf4r", pine_source="//", pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strat)
    await db_session.flush()
    order = Order(
        strategy_id=strat.id, exchange_account_id=acc.id, symbol="BTC/USDT",
        side=OrderSide.buy, type=OrderType.market, quantity=Decimal("0.01"),
        state=state, exchange_order_id=exchange_order_id,
    )
    db_session.add(order)
    await db_session.commit()
    return order


@pytest.mark.asyncio
async def test_cancel_submitted_delegates_to_exchange_task(
    client, mock_clerk_auth, db_session, monkeypatch: pytest.MonkeyPatch
):
    """submitted 주문 cancel → 202 + cancel_order_task.delay 호출, DB 는 submitted 유지."""
    import src.tasks.trading as task_mod

    order = await _setup(
        db_session, mock_clerk_auth, state=OrderState.submitted, exchange_order_id="bybit-x1"
    )
    calls: list[str] = []
    monkeypatch.setattr(task_mod.cancel_order_task, "delay", lambda oid: calls.append(oid))

    resp = await client.post(f"/api/v1/orders/{order.id}/cancel")
    assert resp.status_code == 202, resp.text
    assert calls == [str(order.id)], "cancel_order_task 가 dispatch 돼야 함"

    await db_session.refresh(order)
    assert order.state == OrderState.submitted, "submitted 주문이 DB-only cancel 되면 안 됨 (orphan)"


@pytest.mark.asyncio
async def test_cancel_pending_immediate_db_cancel(
    client, mock_clerk_auth, db_session
):
    """pending 주문 cancel → 200 + 즉시 cancelled (거래소 미발주이므로 안전)."""
    order = await _setup(db_session, mock_clerk_auth, state=OrderState.pending)

    resp = await client.post(f"/api/v1/orders/{order.id}/cancel")
    assert resp.status_code == 200, resp.text

    await db_session.refresh(order)
    assert order.state == OrderState.cancelled

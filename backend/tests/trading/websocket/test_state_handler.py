"""Sprint 12 Phase C — StateHandler TDD.

5 시나리오 (M2 Slim):
1. orderLinkId == Order.id (UUID) → DB transition
2. exchange_order_id fallback (orderLinkId 없거나 invalid)
3. orphan event buffered when Order row 미존재
4. orphan_buffer FIFO eviction at 1000 (G3 #2)
5. Rejected status → Slack alert 호출
"""

from __future__ import annotations

import time
from decimal import Decimal
from uuid import uuid4

import pytest

from src.core.config import Settings
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.websocket.state_handler import StateHandler


def _make_settings() -> Settings:
    """SLACK_WEBHOOK_URL 미설정 — alert silent skip."""
    return Settings()


@pytest.fixture
def session_factory(db_session):
    """test 의 db_session 을 그대로 반환하는 async context manager."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory():
        yield db_session

    return factory


@pytest.fixture
async def sample_order(db_session, strategy, user):
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=acc.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.submitted,
    )
    db_session.add(order)
    await db_session.flush()
    return order, acc


async def test_orderLinkId_lookup_transitions_to_filled(
    sample_order, session_factory, db_session
):
    order, acc = sample_order
    handler = StateHandler(
        session_factory=session_factory, settings=_make_settings()
    )
    await handler.handle_order_event(
        acc.id,
        {
            "orderLinkId": str(order.id),
            "orderId": "EX-123",
            "orderStatus": "Filled",
            "avgPrice": "50000.00",
        },
    )
    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    result = await db_session.execute(stmt)
    refreshed = result.scalar_one()
    assert refreshed.state == OrderState.filled
    assert refreshed.filled_price == Decimal("50000.00")


async def test_invalid_orderLinkId_falls_back_to_exchange_order_id(
    sample_order, session_factory, db_session
):
    """orderLinkId 가 UUID 형식 아니면 exchange_order_id 로 lookup."""
    order, acc = sample_order
    # 미리 exchange_order_id 채워두기
    order.exchange_order_id = "EX-FALLBACK-1"
    db_session.add(order)
    await db_session.flush()

    handler = StateHandler(
        session_factory=session_factory, settings=_make_settings()
    )
    await handler.handle_order_event(
        acc.id,
        {
            "orderLinkId": "not-a-uuid",
            "orderId": "EX-FALLBACK-1",
            "orderStatus": "Cancelled",
        },
    )
    from sqlalchemy import select
    async with session_factory() as s:
        stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
        refreshed = (await s.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.cancelled


async def test_unknown_order_buffered_in_orphan_buffer(session_factory):
    handler = StateHandler(
        session_factory=session_factory, settings=_make_settings()
    )
    fake_id = str(uuid4())
    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": fake_id,
            "orderId": "EX-NEW",
            "orderStatus": "Filled",
        },
    )
    assert fake_id in handler._orphan_buffer
    payload, ts = handler._orphan_buffer[fake_id]
    assert payload["orderStatus"] == "Filled"
    # 5s TTL 안
    assert time.time() - ts < 1.0


async def test_orphan_buffer_fifo_eviction_at_1000(session_factory):
    """codex G3 #2 — FIFO max 1000."""
    handler = StateHandler(
        session_factory=session_factory, settings=_make_settings()
    )
    account_id = uuid4()
    # 1005 개 enqueue → 1000 만 잔존, 가장 먼저 들어간 5개는 eviction
    for i in range(1005):
        await handler.handle_order_event(
            account_id,
            {"orderLinkId": str(uuid4()), "orderStatus": "Filled", "_idx": i},
        )
    assert len(handler._orphan_buffer) == 1000


async def test_rejected_status_triggers_alert(
    sample_order, session_factory, monkeypatch
):
    from unittest.mock import AsyncMock

    mock_alert = AsyncMock(return_value=True)
    order, acc = sample_order
    handler = StateHandler(
        session_factory=session_factory,
        settings=_make_settings(),
        alert_sender=mock_alert,
    )
    await handler.handle_order_event(
        acc.id,
        {
            "orderLinkId": str(order.id),
            "orderId": "EX-REJ-1",
            "orderStatus": "Rejected",
            "rejectReason": "Insufficient margin",
        },
    )
    mock_alert.assert_called_once()
    args = mock_alert.call_args
    title = args[0][1] if len(args[0]) > 1 else args.kwargs["title"]
    assert "Rejected" in title
    context = args[0][3] if len(args[0]) > 3 else args.kwargs.get("context")
    assert context is not None
    assert context["reason"] == "Insufficient margin"

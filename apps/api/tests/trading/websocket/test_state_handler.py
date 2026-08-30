"""Sprint 12 Phase C — StateHandler TDD.

4 시나리오 (M2 Slim, BL-448 로 5→4):
1. orderLinkId == Order.id (UUID) → DB transition
2. exchange_order_id fallback (orderLinkId 없거나 invalid)
3. Order row 미존재 → 전이 없이 폐기 + 폐기 축 계상 (구 "orphan event buffered")
4. Rejected status → Slack alert 호출
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.common.metrics import qb_ws_orphan_discarded_total
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
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.websocket_order_event_service import WebSocketOrderEventService
from src.trading.websocket.state_handler import StateHandler


def _make_settings() -> Settings:
    """SLACK_WEBHOOK_URL 미설정 — alert silent skip."""
    return Settings()


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


async def test_orderLinkId_lookup_transitions_to_filled(sample_order, db_session):
    order, acc = sample_order
    handler = WebSocketOrderEventService(
        repo=OrderRepository(db_session), settings=_make_settings()
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


async def test_filled_trailing_order_enqueues_place_trailing_stop(
    db_session, strategy, user, monkeypatch
):
    """STEP B (Opus B HIGH) — WS Filled winner + trailing 의도 → place_trailing_stop enqueue.

    WS fill 경로는 async 체결의 1차 placement 트리거(EC-1). winner-only(rowcount==1)
    분기 안에서 동기/watchdog/reconciler 와 동일 helper 로 enqueue.
    """
    import src.tasks.trading as trading_mod

    calls: list[dict] = []
    monkeypatch.setattr(
        trading_mod.place_trailing_stop_task, "apply_async", lambda **kw: calls.append(kw)
    )
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
        leverage=5,
        trailing_stop=Decimal("3.0"),
    )
    db_session.add(order)
    await db_session.flush()

    handler = WebSocketOrderEventService(
        repo=OrderRepository(db_session), settings=_make_settings()
    )
    await handler.handle_order_event(
        acc.id,
        {
            "orderLinkId": str(order.id),
            "orderId": "EX-TR",
            "orderStatus": "Filled",
            "avgPrice": "50000.00",
        },
    )
    assert len(calls) == 1
    assert calls[0]["args"] == [str(order.id)]


async def test_filled_non_trailing_order_does_not_enqueue(sample_order, db_session, monkeypatch):
    """trailing 의도 없는 fill → enqueue 안 함(회귀 0)."""
    import src.tasks.trading as trading_mod

    calls: list[dict] = []
    monkeypatch.setattr(
        trading_mod.place_trailing_stop_task, "apply_async", lambda **kw: calls.append(kw)
    )
    order, acc = sample_order  # trailing_stop=None
    handler = WebSocketOrderEventService(
        repo=OrderRepository(db_session), settings=_make_settings()
    )
    await handler.handle_order_event(
        acc.id,
        {"orderLinkId": str(order.id), "orderId": "EX-1", "orderStatus": "Filled", "avgPrice": "5"},
    )
    assert calls == []


async def test_invalid_orderLinkId_falls_back_to_exchange_order_id(sample_order, db_session):
    """orderLinkId 가 UUID 형식 아니면 exchange_order_id 로 lookup."""
    order, acc = sample_order
    # 미리 exchange_order_id 채워두기
    order.exchange_order_id = "EX-FALLBACK-1"
    db_session.add(order)
    await db_session.flush()

    handler = WebSocketOrderEventService(
        repo=OrderRepository(db_session), settings=_make_settings()
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

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.cancelled


async def test_unknown_order_is_discarded_without_transition(db_session):
    """로컬 행이 없는 이벤트는 폐기되고 아무 전이도 일으키지 않는다 (BL-448).

    ★종전 이름은 `test_unknown_order_buffered_in_orphan_buffer` 였고 5초 버퍼의 내부
    (`handler._orphan_buffer[fake_id]` 와 항목의 타임스탬프)를 직접 단언했다. 그 버퍼를
    읽는 프로덕션 경로가 없었으므로(`replay_orphan` 호출자 0) 버퍼째 걷어냈고, 여기서 잴
    것은 **관측 가능한 행위** — 전이 없음 + 폐기 계상 — 로 바뀌었다.
    `_discard_orphan` 의 reason 축은 `test_state_handler_gaps.py` 가 잰다.
    """
    handler = WebSocketOrderEventService(
        repo=OrderRepository(db_session), settings=_make_settings()
    )
    spy = AsyncMock(return_value=0)
    handler._apply_transition = spy  # type: ignore[method-assign]
    account_id = uuid4()
    before = qb_ws_orphan_discarded_total.labels(reason="terminal_event_lost")._value.get()  # type: ignore[attr-defined]

    await handler.handle_order_event(
        account_id,
        {
            "orderLinkId": str(uuid4()),
            "orderId": "EX-NEW",
            "orderStatus": "Filled",
        },
    )

    spy.assert_not_awaited()
    assert (
        qb_ws_orphan_discarded_total.labels(reason="terminal_event_lost")._value.get()  # type: ignore[attr-defined]
        == before + 1
    )


# tombstone — `test_orphan_buffer_fifo_eviction_at_1000` (codex G3 #2, FIFO max 1000) 은
# BL-448 에서 삭제했다. 재던 대상인 버퍼 자체가 사라졌고, 그 버퍼는 재생 장치가 아니라
# 지연된 폐기장이었다(호출자 0). 원문은 git history 에 있다.


async def test_rejected_status_triggers_alert(sample_order, db_session, monkeypatch):
    from unittest.mock import AsyncMock

    mock_alert = AsyncMock(return_value=True)
    order, acc = sample_order
    handler = WebSocketOrderEventService(
        repo=OrderRepository(db_session),
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


async def test_state_handler_forwards_transport_payload_to_callback():
    """Transport adapter는 DB를 열지 않고 조립된 callback만 호출한다."""
    callback = AsyncMock()
    handler = StateHandler(callback)
    account_id = uuid4()
    payload = {"orderStatus": "Filled"}

    await handler.handle_order_event(account_id, payload)

    callback.assert_awaited_once_with(account_id, payload)

"""[BL-762] 라우터 계층 리팩터가 깨뜨릴 수 있는 계약을 고정한다.

HTTP 응답과 소유권 경계를 현재 동작 그대로 회귀 테스트로 보존한다.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    KillSwitchEvent,
    KillSwitchTriggerType,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


async def _create_other_user(db_session) -> User:
    other_user = User(
        auth_subject=f"router-contract-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
    )
    db_session.add(other_user)
    await db_session.flush()
    return other_user


async def _create_order(db_session, user: User, *, state: OrderState) -> Order:
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    strategy = Strategy(
        user_id=user.id,
        name="router-contract-order",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add_all([account, strategy])
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=state,
    )
    db_session.add(order)
    await db_session.commit()
    return order


async def _create_live_session(db_session, user: User) -> LiveSignalSession:
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    strategy = Strategy(
        user_id=user.id,
        name="router-contract-session",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add_all([account, strategy])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add(session)
    await db_session.commit()
    return session


@pytest.mark.asyncio
async def test_cancel_submitted_ack_detail_is_frozen(
    client, mock_authed_user, db_session, monkeypatch: pytest.MonkeyPatch
):
    """submitted 취소의 202 acknowledgement body는 FE literal 계약이다."""
    import src.tasks.trading as task_mod

    order = await _create_order(db_session, mock_authed_user, state=OrderState.submitted)
    calls: list[str] = []
    monkeypatch.setattr(
        task_mod.cancel_order_task, "delay", lambda order_id: calls.append(order_id)
    )

    response = await client.post(f"/api/v1/orders/{order.id}/cancel")

    assert response.status_code == 202, response.text
    assert response.json() == {
        "order_id": str(order.id),
        "state": "submitted",
        "detail": "exchange cancel requested",
    }
    assert calls == [str(order.id)]


@pytest.mark.asyncio
async def test_cancel_rejects_other_users_order(client, mock_authed_user, db_session):
    """다른 사용자의 pending 주문은 취소할 수 없고 상태도 보존된다."""
    other_user = await _create_other_user(db_session)
    order = await _create_order(db_session, other_user, state=OrderState.pending)

    response = await client.post(f"/api/v1/orders/{order.id}/cancel")

    assert response.status_code == 404, response.text
    await db_session.refresh(order)
    assert order.state == OrderState.pending


@pytest.mark.asyncio
async def test_get_order_rejects_other_users_order(client, mock_authed_user, db_session):
    """다른 사용자의 주문 조회는 존재 여부를 드러내지 않고 404다."""
    other_user = await _create_other_user(db_session)
    order = await _create_order(db_session, other_user, state=OrderState.pending)

    response = await client.get(f"/api/v1/orders/{order.id}")

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_live_session_events_reject_other_users_session(client, mock_authed_user, db_session):
    """다른 사용자의 LiveSignalSession event log 조회는 404다."""
    other_user = await _create_other_user(db_session)
    live_session = await _create_live_session(db_session, other_user)

    response = await client.get(f"/api/v1/live-sessions/{live_session.id}/events")

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_resolve_kill_switch_rejects_other_users_event(client, mock_authed_user, db_session):
    """다른 사용자의 Kill Switch event는 해제할 수 없고 활성 상태를 유지한다."""
    other_user = await _create_other_user(db_session)
    strategy = Strategy(
        user_id=other_user.id,
        name="router-contract-kill-switch",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("15"),
        threshold=Decimal("10"),
    )
    db_session.add(event)
    await db_session.commit()

    response = await client.post(f"/api/v1/kill-switch/events/{event.id}/resolve")

    assert response.status_code == 404, response.text
    await db_session.refresh(event)
    assert event.resolved_at is None

"""Sprint 16 BL-027 — state_handler dec winner-only commit-then-dec (codex G.0 P1 #1).

핵심:
- `_apply_transition` 은 rowcount: int return + dec 호출 X (caller responsibility)
- `handle_order_event` 는 session.commit() **성공 후** rowcount==1 winner 일 때만
  qb_active_orders.dec() + alert 발송 (race loser noise 방어)

P1 #1: dec() 가 commit 전 발화 시 commit 실패/rollback → DB 는 active 인데 gauge 만
감소 → drift. Sprint 15 watchdog 표준 (`tasks/trading.py:458` 부근) 의 commit-then-dec
패턴을 동일 적용.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.common.metrics import qb_active_orders
from src.trading.models import (
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.websocket.state_handler import StateHandler


def _build_order(state: OrderState = OrderState.submitted) -> Order:
    return Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=state,
        idempotency_key=None,
        idempotency_payload_hash=None,
        leverage=None,
        margin_mode=None,
    )


def _make_session_factory(session: AsyncMock):
    """async context manager 흉내 — `async with self._session_factory() as session`."""

    class _Ctx:
        async def __aenter__(self) -> AsyncMock:
            return session

        async def __aexit__(self, *_args: object) -> None:
            return None

    return lambda: _Ctx()


# =============================================================================
# _apply_transition: rowcount return + dec 호출 X (caller responsibility)
# =============================================================================


@pytest.mark.asyncio
async def test_apply_transition_filled_returns_rowcount_no_dec() -> None:
    """BL-027: _apply_transition 는 rowcount return + dec 호출 X."""
    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=1)

    handler = StateHandler.__new__(StateHandler)
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(
        repo,
        uuid4(),
        OrderState.filled,
        {"avgPrice": "100.0", "orderId": "abc"},
    )

    assert rc == 1
    # caller responsibility — _apply_transition 자체는 dec 안 함
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_rejected_returns_rowcount_no_dec() -> None:
    repo = AsyncMock()
    repo.transition_to_rejected = AsyncMock(return_value=1)

    handler = StateHandler.__new__(StateHandler)
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(
        repo, uuid4(), OrderState.rejected, {"rejectReason": "fund"}
    )

    assert rc == 1
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_cancelled_returns_rowcount_no_dec() -> None:
    repo = AsyncMock()
    repo.transition_to_cancelled = AsyncMock(return_value=1)

    handler = StateHandler.__new__(StateHandler)
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(
        repo, uuid4(), OrderState.cancelled, {}
    )

    assert rc == 1
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_loser_returns_zero() -> None:
    """rowcount==0 loser — 다른 path 가 이미 transition. caller 가 dec 안 해야."""
    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=0)

    handler = StateHandler.__new__(StateHandler)
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(
        repo,
        uuid4(),
        OrderState.filled,
        {"avgPrice": "100.0", "orderId": "abc"},
    )

    assert rc == 0
    assert qb_active_orders._value.get() == 1.0


# =============================================================================
# handle_order_event: commit-then-dec winner-only + alert winner-only
# =============================================================================


@pytest.mark.asyncio
async def test_handle_order_event_filled_winner_commits_then_decs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rowcount==1 winner: session.commit() 호출 후 qb_active_orders 1 → 0."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_filled = AsyncMock(return_value=1)

    session = AsyncMock()
    session.commit = AsyncMock()

    settings = MagicMock()
    handler = StateHandler(
        session_factory=_make_session_factory(session),
        settings=settings,
        alert_sender=AsyncMock(return_value=True),
    )
    # OrderRepository 는 handle_order_event 내부에서 OrderRepository(session) 으로 생성.
    # repo 객체를 그대로 주입 못 하므로 monkeypatch 로 OrderRepository 클래스 바이패스.
    from src.trading.websocket import state_handler as sh_module

    monkeypatch.setattr(sh_module, "OrderRepository", lambda _: repo)

    qb_active_orders.set(1.0)

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Filled",
            "orderId": "exchange-abc",
            "avgPrice": "100.0",
        },
    )

    session.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 0.0


@pytest.mark.asyncio
async def test_handle_order_event_filled_loser_commits_no_dec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rowcount==0 loser: commit 호출 OK (no-op UPDATE) 하지만 dec X."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_filled = AsyncMock(return_value=0)  # loser

    session = AsyncMock()
    session.commit = AsyncMock()

    settings = MagicMock()
    handler = StateHandler(
        session_factory=_make_session_factory(session),
        settings=settings,
        alert_sender=AsyncMock(return_value=True),
    )

    from src.trading.websocket import state_handler as sh_module

    monkeypatch.setattr(sh_module, "OrderRepository", lambda _: repo)

    qb_active_orders.set(1.0)

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Filled",
            "orderId": "exchange-abc",
            "avgPrice": "100.0",
        },
    )

    session.commit.assert_awaited_once()  # commit 자체는 OK (no-op)
    assert qb_active_orders._value.get() == 1.0  # dec X — race loser


@pytest.mark.asyncio
async def test_handle_order_event_rejected_loser_no_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rejected loser: alert 도 winner-only. race noise 방어."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_rejected = AsyncMock(return_value=0)  # loser

    session = AsyncMock()
    session.commit = AsyncMock()

    settings = MagicMock()
    alert_sender = AsyncMock(return_value=True)
    handler = StateHandler(
        session_factory=_make_session_factory(session),
        settings=settings,
        alert_sender=alert_sender,
    )

    from src.trading.websocket import state_handler as sh_module

    monkeypatch.setattr(sh_module, "OrderRepository", lambda _: repo)

    qb_active_orders.set(1.0)

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Rejected",
            "orderId": "exchange-abc",
            "rejectReason": "fund",
        },
    )

    session.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 1.0
    alert_sender.assert_not_awaited()  # race loser → alert noise 방어


@pytest.mark.asyncio
async def test_handle_order_event_filled_commit_failure_no_dec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex G.0 P1 #1: UPDATE 성공 → commit 실패 → dec 도달 안 함 (silent corruption 방어)."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_filled = AsyncMock(return_value=1)

    session = AsyncMock()
    session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))

    settings = MagicMock()
    handler = StateHandler(
        session_factory=_make_session_factory(session),
        settings=settings,
        alert_sender=AsyncMock(return_value=True),
    )

    from src.trading.websocket import state_handler as sh_module

    monkeypatch.setattr(sh_module, "OrderRepository", lambda _: repo)

    qb_active_orders.set(1.0)

    with pytest.raises(RuntimeError):
        await handler.handle_order_event(
            uuid4(),
            {
                "orderLinkId": str(order.id),
                "orderStatus": "Filled",
                "orderId": "exchange-abc",
                "avgPrice": "100.0",
            },
        )

    # commit 실패 → dec 발화 X → DB rollback 시 gauge 일관 (drift 방어)
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_handle_order_event_rejected_winner_alerts_and_decs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rejected winner: commit + dec + alert 모두 발화."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_rejected = AsyncMock(return_value=1)

    session = AsyncMock()
    session.commit = AsyncMock()

    settings = MagicMock()
    alert_sender = AsyncMock(return_value=True)
    handler = StateHandler(
        session_factory=_make_session_factory(session),
        settings=settings,
        alert_sender=alert_sender,
    )

    from src.trading.websocket import state_handler as sh_module

    monkeypatch.setattr(sh_module, "OrderRepository", lambda _: repo)

    qb_active_orders.set(1.0)

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Rejected",
            "orderId": "exchange-abc",
            "rejectReason": "fund",
        },
    )

    session.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 0.0
    alert_sender.assert_awaited_once()

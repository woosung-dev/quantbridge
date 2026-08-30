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

from src.common.metrics import qb_active_orders, qb_partial_fill_total
from src.trading.models import (
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.services.websocket_order_event_service import WebSocketOrderEventService


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


# =============================================================================
# _apply_transition: rowcount return + dec 호출 X (caller responsibility)
# =============================================================================


@pytest.mark.asyncio
async def test_apply_transition_filled_returns_rowcount_no_dec() -> None:
    """BL-027: _apply_transition 는 rowcount return + dec 호출 X."""
    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=1)

    handler = WebSocketOrderEventService(repo=repo, settings=MagicMock())
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(
        uuid4(),
        OrderState.filled,
        {"avgPrice": "100.0", "cumExecQty": "0.0005", "orderId": "abc"},
    )

    assert rc == 1
    assert repo.transition_to_filled.await_args.kwargs["filled_quantity"] == Decimal("0.0005")
    # caller responsibility — _apply_transition 자체는 dec 안 함
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_rejected_returns_rowcount_no_dec() -> None:
    repo = AsyncMock()
    repo.transition_to_rejected = AsyncMock(return_value=1)

    handler = WebSocketOrderEventService(repo=repo, settings=MagicMock())
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(uuid4(), OrderState.rejected, {"rejectReason": "fund"})

    assert rc == 1
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_cancelled_returns_rowcount_no_dec() -> None:
    repo = AsyncMock()
    repo.transition_to_cancelled = AsyncMock(return_value=1)

    handler = WebSocketOrderEventService(repo=repo, settings=MagicMock())
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(uuid4(), OrderState.cancelled, {})

    assert rc == 1
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_loser_returns_zero() -> None:
    """rowcount==0 loser — 다른 path 가 이미 transition. caller 가 dec 안 해야."""
    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=0)

    handler = WebSocketOrderEventService(repo=repo, settings=MagicMock())
    qb_active_orders.set(1.0)

    rc = await handler._apply_transition(
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

    trace: list[str] = []

    async def _commit() -> None:
        trace.append("commit")

    repo.commit = AsyncMock(side_effect=_commit)

    settings = MagicMock()
    user_id = uuid4()
    handler = WebSocketOrderEventService(
        repo=repo,
        settings=settings,
        alert_sender=AsyncMock(return_value=True),
        user_id=user_id,
    )
    import src.trading.services.websocket_order_event_service as service_module

    async def _publish(*_args: object, **_kwargs: object) -> None:
        trace.append("publish")

    publisher = AsyncMock(side_effect=_publish)
    monkeypatch.setattr(service_module, "publish_realtime", publisher)

    qb_active_orders.set(1.0)
    partial_counter = qb_partial_fill_total.labels(source="ws", kind="entry")
    before_partial = partial_counter._value.get()

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Filled",
            "orderId": "exchange-abc",
            "avgPrice": "100.0",
            "cumExecQty": "0.0005",
        },
    )

    repo.commit.assert_awaited_once()
    publisher.assert_awaited_once_with(
        str(user_id),
        "order_update",
        {
            "order_id": str(order.id),
            "state": "filled",
            "symbol": order.symbol,
            "side": order.side.value,
            "source": "ws",
        },
    )
    assert trace == ["commit", "publish"]
    assert qb_active_orders._value.get() == 0.0
    assert partial_counter._value.get() == before_partial + 1


@pytest.mark.asyncio
async def test_handle_order_event_partial_fill_splits_ws_metric_by_order_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry_order = _build_order()
    close_order = _build_order()
    close_order.reduce_only = True

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(side_effect=[entry_order, close_order])
    repo.transition_to_filled = AsyncMock(return_value=1)
    repo.commit = AsyncMock()

    handler = WebSocketOrderEventService(
        repo=repo,
        settings=MagicMock(),
        alert_sender=AsyncMock(return_value=True),
        user_id=uuid4(),
    )
    import src.tasks.trading as task_mod
    import src.trading.services.websocket_order_event_service as service_module

    monkeypatch.setattr(service_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(task_mod, "_enqueue_trailing_if_intended", lambda _order: None)
    monkeypatch.setattr(task_mod, "_enqueue_closed_pnl_refresh", lambda _order: None)
    monkeypatch.setattr(task_mod, "_enqueue_conditional_reversal_measure", lambda _order: None)

    entry_counter = qb_partial_fill_total.labels(source="ws", kind="entry")
    close_counter = qb_partial_fill_total.labels(source="ws", kind="close")
    entry_before = entry_counter._value.get()
    close_before = close_counter._value.get()

    for order in (entry_order, close_order):
        await handler.handle_order_event(
            uuid4(),
            {
                "orderLinkId": str(order.id),
                "orderStatus": "Filled",
                "orderId": f"exchange-{order.id}",
                "avgPrice": "100.0",
                "cumExecQty": "0.0005",
            },
        )

    assert entry_counter._value.get() == entry_before + 1
    assert close_counter._value.get() == close_before + 1


@pytest.mark.asyncio
async def test_partial_fill_metric_failure_does_not_stop_fill_postprocessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★계측 실패가 체결 후처리를 끊지 않는다 (2026-08-01 codex 적대 리뷰 MAJOR).

    `kind` 축을 추가하면 `{source,kind}` 조합이 **처음 할당**되는데, multiprocess mmap
    할당이 실패하면 `.labels()` 가 던진다. 이 호출부는 DB commit **뒤**, trailing·PnL
    후속 enqueue **앞**이라 던지면 후처리가 통째로 중단된다.

    ★**이 테스트는 그 사고를 재현한다** — `labels` 가 `OSError` 를 내도 뒤따르는
    `_enqueue_*` 세 훅이 전부 호출돼야 한다. `record_partial_fill` 의 `record_metric_safely`
    래핑을 벗기면 이 테스트가 죽는다(판별력).
    """
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_filled = AsyncMock(return_value=1)
    repo.commit = AsyncMock()

    handler = WebSocketOrderEventService(
        repo=repo,
        settings=MagicMock(),
        alert_sender=AsyncMock(return_value=True),
        user_id=uuid4(),
    )
    import src.common.metrics as metrics_mod
    import src.tasks.trading as task_mod

    called: list[str] = []
    import src.trading.services.websocket_order_event_service as service_module

    monkeypatch.setattr(service_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(
        task_mod, "_enqueue_trailing_if_intended", lambda _order: called.append("trailing")
    )
    monkeypatch.setattr(
        task_mod, "_enqueue_closed_pnl_refresh", lambda _order: called.append("pnl")
    )
    monkeypatch.setattr(
        task_mod, "_enqueue_conditional_reversal_measure", lambda _order: called.append("reversal")
    )

    def _explode(**_kwargs: object) -> object:
        raise OSError("mmap allocation failed")

    monkeypatch.setattr(metrics_mod.qb_partial_fill_total, "labels", _explode)

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Filled",
            "orderId": f"exchange-{order.id}",
            "avgPrice": "100.0",
            "cumExecQty": "0.0005",
        },
    )

    assert called == ["trailing", "pnl", "reversal"]


@pytest.mark.asyncio
async def test_active_orders_metric_failure_does_not_stop_fill_postprocessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """활성 주문 계측 오류가 체결 후처리 세 갈래를 끊지 않는다."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_filled = AsyncMock(return_value=1)
    repo.commit = AsyncMock()

    handler = WebSocketOrderEventService(
        repo=repo,
        settings=MagicMock(),
        alert_sender=AsyncMock(return_value=True),
        user_id=uuid4(),
    )
    import src.common.metrics as metrics_mod
    import src.tasks.trading as task_mod

    called: list[str] = []
    import src.trading.services.websocket_order_event_service as service_module

    monkeypatch.setattr(service_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(
        task_mod, "_enqueue_trailing_if_intended", lambda _order: called.append("trailing")
    )
    monkeypatch.setattr(
        task_mod, "_enqueue_closed_pnl_refresh", lambda _order: called.append("pnl")
    )
    monkeypatch.setattr(
        task_mod, "_enqueue_conditional_reversal_measure", lambda _order: called.append("reversal")
    )

    def _explode() -> None:
        raise OSError("mmap allocation failed")

    monkeypatch.setattr(metrics_mod.qb_active_orders, "dec", _explode)

    await handler.handle_order_event(
        uuid4(),
        {
            "orderLinkId": str(order.id),
            "orderStatus": "Filled",
            "orderId": f"exchange-{order.id}",
            "avgPrice": "100.0",
            "cumExecQty": "0.0005",
        },
    )

    assert called == ["trailing", "pnl", "reversal"]


@pytest.mark.asyncio
async def test_handle_order_event_filled_loser_commits_no_dec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rowcount==0 loser: commit 호출 OK (no-op UPDATE) 하지만 dec X."""
    order = _build_order()

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=order)
    repo.transition_to_filled = AsyncMock(return_value=0)  # loser
    repo.commit = AsyncMock()

    settings = MagicMock()
    user_id = uuid4()
    handler = WebSocketOrderEventService(
        repo=repo,
        settings=settings,
        alert_sender=AsyncMock(return_value=True),
        user_id=user_id,
    )

    import src.trading.services.websocket_order_event_service as service_module

    publisher = AsyncMock()
    monkeypatch.setattr(service_module, "publish_realtime", publisher)

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

    repo.commit.assert_awaited_once()  # commit 자체는 OK (no-op)
    publisher.assert_not_awaited()
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
    repo.commit = AsyncMock()

    settings = MagicMock()
    alert_sender = AsyncMock(return_value=True)
    handler = WebSocketOrderEventService(
        repo=repo,
        settings=settings,
        alert_sender=alert_sender,
    )

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

    repo.commit.assert_awaited_once()
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
    repo.commit = AsyncMock(side_effect=RuntimeError("commit failed"))

    settings = MagicMock()
    user_id = uuid4()
    handler = WebSocketOrderEventService(
        repo=repo,
        settings=settings,
        alert_sender=AsyncMock(return_value=True),
        user_id=user_id,
    )

    import src.trading.services.websocket_order_event_service as service_module

    publisher = AsyncMock()
    monkeypatch.setattr(service_module, "publish_realtime", publisher)

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
    publisher.assert_not_awaited()
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
    repo.commit = AsyncMock()

    settings = MagicMock()
    alert_sender = AsyncMock(return_value=True)
    handler = WebSocketOrderEventService(
        repo=repo,
        settings=settings,
        alert_sender=alert_sender,
    )

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

    repo.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 0.0
    alert_sender.assert_awaited_once()

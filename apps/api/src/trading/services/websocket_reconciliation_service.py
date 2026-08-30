"""Private WebSocket reconciliation의 DB 유스케이스."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from src.common.alert import send_critical_alert
from src.common.metrics import qb_active_orders, qb_ws_reconcile_unknown_total, record_partial_fill
from src.common.metrics_multiproc import record_metric_safely
from src.core.config import Settings
from src.trading.models import Order, OrderState
from src.trading.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = frozenset(
    {"Cancelled", "Rejected", "Filled", "closed", "canceled", "rejected"}
)
_STATUS_MAP: dict[str, OrderState] = {
    "Filled": OrderState.filled,
    "Cancelled": OrderState.cancelled,
    "Rejected": OrderState.rejected,
    "closed": OrderState.filled,
    "canceled": OrderState.cancelled,
    "rejected": OrderState.rejected,
}


class ReconcileFetcher(Protocol):
    async def fetch_open_orders(self, account_id: UUID) -> list[dict[str, Any]]: ...

    async def fetch_recent_orders(
        self, account_id: UUID, *, limit: int = 50
    ) -> list[dict[str, Any]]: ...


AlertSender = Callable[..., Awaitable[bool]]


class WebSocketReconciliationService:
    """로컬 active order와 exchange snapshot을 대조해 terminal state만 반영한다."""

    def __init__(
        self,
        *,
        repo: OrderRepository,
        fetcher: ReconcileFetcher,
        settings: Settings,
        alert_sender: AlertSender | None = None,
    ) -> None:
        self._repo = repo
        self._fetcher = fetcher
        self._settings = settings
        self._alert_sender = alert_sender or send_critical_alert

    async def run(self, *, account_id: UUID) -> None:
        local_active = await self._repo.list_active_by_exchange_account(account_id)
        if not local_active:
            return

        exchange_orders = [
            *await self._fetcher.fetch_open_orders(account_id),
            *await self._fetcher.fetch_recent_orders(account_id, limit=50),
        ]
        winners: list[tuple[Order, OrderState, dict[str, Any]]] = []
        for local in local_active:
            exchange_order = self._find_match(exchange_orders, str(local.id))
            if exchange_order is None:
                await self._handle_unknown(local, account_id)
                continue

            status = exchange_order.get("status", "")
            if status not in _TERMINAL_STATUSES:
                continue
            new_state = _STATUS_MAP[status]
            if new_state != local.state:
                rowcount = await self._apply_transition(local, new_state, exchange_order)
                if rowcount == 1:
                    winners.append((local, new_state, exchange_order))

        # 기존 cycle 의미를 보존한다. active order가 하나 이상이면 no-op update/unknown만
        # 있었더라도 한 번 확정해 같은 session lifecycle을 유지한다.
        await self._repo.commit()
        for local, new_state, exchange_order in winners:
            await self._after_committed_winner(local, new_state, exchange_order)

    @staticmethod
    def _find_match(exchange_orders: list[dict[str, Any]], local_id: str) -> dict[str, Any] | None:
        for order in exchange_orders:
            client_id = (
                order.get("clientOrderId") or order.get("orderLinkId") or order.get("clOrdId")
            )
            if client_id == local_id:
                return order
        return None

    async def _handle_unknown(self, local: Order, account_id: UUID) -> None:
        record_metric_safely(qb_ws_reconcile_unknown_total.inc)
        age_hours = (datetime.now(UTC) - local.created_at).total_seconds() / 3600
        stale_marker = " (stale >1h)" if age_hours > 1 else ""
        try:
            await self._alert_sender(
                self._settings,
                f"Order Reconcile Unknown{stale_marker}",
                f"Order {local.id} not found in exchange open/recent. "
                f"Local state {local.state} unchanged. Manual verification needed.",
                {
                    "order_id": str(local.id),
                    "account_id": str(account_id),
                    "local_state": local.state,
                    "age_hours": f"{age_hours:.1f}",
                    "symbol": local.symbol,
                },
            )
        except Exception as exc:
            logger.warning("reconcile_alert_failed err=%s", exc)

    async def _apply_transition(
        self,
        local: Order,
        new_state: OrderState,
        exchange_order: dict[str, Any],
    ) -> int:
        now = datetime.now(UTC)
        if new_state == OrderState.filled:
            avg = exchange_order.get("average") or exchange_order.get("avgPrice")
            filled = exchange_order.get("filled") or exchange_order.get("cumExecQty")
            rowcount = await self._repo.transition_to_filled(
                local.id,
                exchange_order_id=str(exchange_order.get("id", local.exchange_order_id or "")),
                filled_price=Decimal(str(avg)) if avg else None,
                filled_quantity=Decimal(str(filled)) if filled else None,
                filled_at=now,
            )
        elif new_state == OrderState.cancelled:
            rowcount = await self._repo.transition_to_cancelled(local.id, cancelled_at=now)
        elif new_state == OrderState.rejected:
            reason = exchange_order.get("info", {}).get("rejectReason", "reconcile_rejected")
            rowcount = await self._repo.transition_to_rejected(
                local.id, error_message=str(reason), failed_at=now
            )
        else:
            return 0
        logger.info(
            "ws_reconcile_transition order=%s old=%s new=%s rowcount=%d",
            local.id,
            local.state,
            new_state,
            rowcount,
        )
        return rowcount

    @staticmethod
    async def _after_committed_winner(
        local: Order,
        new_state: OrderState,
        exchange_order: dict[str, Any],
    ) -> None:
        record_metric_safely(qb_active_orders.dec)
        if new_state != OrderState.filled:
            return

        filled = exchange_order.get("filled") or exchange_order.get("cumExecQty")
        filled_quantity = Decimal(str(filled)) if filled else None
        if (
            filled_quantity is not None
            and filled_quantity.is_finite()
            and filled_quantity < local.quantity
        ):
            record_partial_fill(source="reconciler", reduce_only=local.reduce_only)

        from src.tasks.trading import (
            _enqueue_closed_pnl_refresh,
            _enqueue_conditional_reversal_measure,
            _enqueue_trailing_if_intended,
        )

        _enqueue_trailing_if_intended(local)
        _enqueue_closed_pnl_refresh(local)
        _enqueue_conditional_reversal_measure(local)

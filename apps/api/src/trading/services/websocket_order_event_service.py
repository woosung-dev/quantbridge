"""Private WebSocket order event의 DB 유스케이스.

전송 계층은 payload를 전달할 뿐이고, 이 서비스가 Repository를 통해 상태 전이와
트랜잭션 경계를 소유한다. 모든 winner 부수효과는 commit 성공 뒤에만 실행한다.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, cast
from uuid import UUID

from src.common.alert import send_critical_alert
from src.common.metrics import (
    qb_active_orders,
    qb_ws_orphan_discarded_total,
    qb_ws_orphan_event_total,
    record_partial_fill,
)
from src.common.metrics_multiproc import _count_safely, record_metric_safely
from src.core.config import Settings
from src.trading.models import Order, OrderState
from src.trading.order_fill_evidence import has_recorded_order_fill
from src.trading.providers import bybit_cumulative_execution_value
from src.trading.realtime_publisher import publish_realtime
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_risk_service import (
    CodeRiskError,
    CodeRiskReconciliationPending,
    CodeRiskService,
    RiskCommand,
)
from src.trading.services.native_sl_observation_service import (
    NativeSLObservationService,
    NativeSLParentPending,
    is_native_sl,
)

logger = logging.getLogger(__name__)

_BYBIT_TERMINAL_MAP: dict[str, OrderState] = {
    "Filled": OrderState.filled,
    "Cancelled": OrderState.cancelled,
    "Rejected": OrderState.rejected,
}

AlertSender = Callable[..., Awaitable[bool]]


class WebSocketOrderEventService:
    """한 WebSocket order event를 DB에 반영한다."""

    def __init__(
        self,
        *,
        repo: OrderRepository,
        settings: Settings,
        alert_sender: AlertSender | None = None,
        user_id: UUID | None = None,
        risk_service: CodeRiskService | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._alert_sender = alert_sender or send_critical_alert
        self._user_id = user_id
        self._risk_service = risk_service

    async def handle_order_event(
        self, account_id: UUID, payload: dict[str, Any]
    ) -> list[RiskCommand] | None:
        if self._risk_service is not None and (
            payload.get("parentOrderLinkId")
            or payload.get("createType") in {"CreateByStopLoss", "CreateByTrailingStop"}
        ):
            try:
                binding = await NativeSLObservationService(self._repo).bind(account_id, payload)
            except NativeSLParentPending as pending:
                commands = await self._risk_service.request_signal(
                    pending.session_id, pending.generation, "close", commit=False
                )
                await self._repo.commit()
                return commands
            if binding is not None:
                return await self._handle_code_order(binding[0], binding[1], account_id)
            # 부모 client ID가 child 자신의 ID처럼 실려도 부모 진입을 갱신하지 않는다.
            self._discard_orphan(str(payload.get("orderId", "")), payload, account_id)
            return None
        order_link_id = payload.get("orderLinkId")
        exchange_order_id = payload.get("orderId")

        order: Order | None = None
        if order_link_id:
            with contextlib.suppress(ValueError):
                order = await self._repo.get_by_id(UUID(str(order_link_id)))
        if order is None and exchange_order_id:
            order = await self._repo.get_by_exchange_order_id(
                str(exchange_order_id), account_id=account_id
            )

        if order is None:
            self._discard_orphan(str(order_link_id or exchange_order_id or ""), payload, account_id)
            return None

        if order.exchange_account_id != account_id:
            raise CodeRiskError("주문 계정 귀속이 올바르지 않습니다")
        if is_native_sl(order):
            raise CodeRiskReconciliationPending("native SL의 명시 부모 증거를 기다립니다")
        if order.risk_context is not None:
            return await self._handle_code_order(order, payload, account_id)

        new_state = _BYBIT_TERMINAL_MAP.get(str(payload.get("orderStatus", "")))
        if new_state is None:
            return None

        rowcount = await self._apply_transition(order.id, new_state, payload)
        await self._repo.commit()
        if rowcount == 1:
            await self._after_committed_winner(order, new_state, payload, account_id)
        return None

    async def _handle_code_order(
        self, order: Order, payload: dict[str, Any], account_id: UUID
    ) -> list[RiskCommand]:
        """새 원장 주문만 부분 체결을 반영한다. 두 원장은 같은 commit으로 확정한다."""
        if self._risk_service is None or order.exchange_account_id != account_id:
            raise CodeRiskError("코드 리스크 처리기 또는 주문 계정 귀속이 올바르지 않습니다")
        status = str(payload.get("orderStatus", ""))
        new_state = _BYBIT_TERMINAL_MAP.get(status)
        if status == "PartiallyFilledCanceled":
            new_state = OrderState.cancelled
        if new_state is None and status != "PartiallyFilled":
            if is_native_sl(order):
                await self._repo.commit()
            return []
        context = order.risk_context or {}
        try:
            session_id = UUID(str(context["session_id"]))
            generation = int(str(context["generation"]))
            role = str(context["role"])
            raw_quantity = payload.get("cumExecQty", payload.get("filled"))
            quantity = Decimal(str(raw_quantity))
            if not quantity.is_finite() or quantity < 0 or generation < 1:
                raise ValueError("invalid fill")
        except (KeyError, ValueError, InvalidOperation) as exc:
            raise CodeRiskError(
                "코드 주문의 누적 체결 또는 리스크 귀속이 올바르지 않습니다"
            ) from exc
        if is_native_sl(order) and payload.get("_native_historical") is True:
            await self._native_pnl(order, payload, quantity, new_state)
            await self._repo.commit()
            return []
        price = None
        if new_state in {OrderState.cancelled, OrderState.rejected} and quantity > 0:
            average = payload.get("avgPrice") or payload.get("average")
            try:
                price = Decimal(str(average)) if average not in (None, "") else None
            except InvalidOperation as exc:
                raise CodeRiskReconciliationPending("부분 체결 평균가 증거를 기다립니다") from exc
            if price is None or not price.is_finite() or price <= 0:
                raise CodeRiskReconciliationPending("부분 체결 평균가 증거를 기다립니다")
        if role == "entry":
            value = Decimal(0) if quantity == 0 else bybit_cumulative_execution_value(payload)
            if value is None:
                raise CodeRiskReconciliationPending("진입 누적 체결대금 증거를 기다립니다")
            if not value.is_finite() or value < 0:
                raise CodeRiskError("코드 진입 누적 체결대금이 올바르지 않습니다")
            commands = await self._risk_service.record_entry_fill(
                session_id,
                generation,
                order.id,
                cumulative_quantity=quantity,
                cumulative_value=value,
                terminal=new_state is not None,
                commit=False,
            )
        elif role in ("partial_tp", "stop_loss", "trailing_stop", "close"):
            commands = await self._risk_service.record_exit_fill(
                session_id,
                generation,
                order.id,
                role=cast(Literal["partial_tp", "stop_loss", "trailing_stop", "close"], role),
                cumulative_quantity=quantity,
                terminal=new_state is not None and bool(payload.get("orderId")),
                commit=False,
            )
        else:
            raise CodeRiskError("알 수 없는 코드 주문 역할입니다")
        rowcount = 0
        if new_state in {OrderState.cancelled, OrderState.rejected}:
            exchange_id = payload.get("orderId")
            if isinstance(exchange_id, str) and exchange_id:
                await self._repo.attach_exchange_order_id(order.id, exchange_id)
            if new_state == OrderState.cancelled:
                rowcount = await self._repo.transition_to_cancelled(
                    order.id,
                    cancelled_at=datetime.now(UTC),
                    filled_quantity=quantity,
                    filled_price=price,
                )
            else:
                rowcount = await self._repo.transition_to_rejected(
                    order.id,
                    error_message=f"ws_rejected: {payload.get('rejectReason', 'ws_rejected')}",
                    failed_at=datetime.now(UTC),
                    filled_quantity=quantity,
                    filled_price=price,
                )
        elif new_state is not None:
            rowcount = await self._apply_transition(order.id, new_state, payload)
        if is_native_sl(order):
            await self._native_pnl(order, payload, quantity, new_state)
        await self._repo.commit()
        if rowcount == 1 and new_state is not None:
            await self._after_committed_winner(order, new_state, payload, account_id)
        return commands

    async def _native_pnl(
        self, order: Order, payload: dict[str, Any], quantity: Decimal, terminal: OrderState | None
    ) -> None:
        if terminal is None or quantity <= 0 or payload.get("closedPnl") in (None, ""):
            return
        try:
            pnl = Decimal(str(payload["closedPnl"]))
        except InvalidOperation as exc:
            raise CodeRiskReconciliationPending("native SL 손익 증거를 기다립니다") from exc
        if not pnl.is_finite():
            raise CodeRiskReconciliationPending("native SL 손익이 유한하지 않습니다")
        if order.realized_pnl_synced_at is not None and order.realized_pnl != pnl:
            raise CodeRiskReconciliationPending("native SL의 확정 손익 증거가 다릅니다")
        await self._repo.record_native_sl_pnl(order, quantity=quantity, pnl=pnl)

    def _discard_orphan(self, key: str, payload: dict[str, Any], account_id: UUID) -> None:
        """로컬 행 없는 이벤트는 집계·로그만 남기고 폐기한다."""
        status = str(payload.get("orderStatus", "") or "")
        reason = "terminal_event_lost" if status in _BYBIT_TERMINAL_MAP else "non_terminal_ignored"
        record_metric_safely(qb_ws_orphan_event_total.inc)
        _count_safely(qb_ws_orphan_discarded_total, reason=reason)

        log = logger.warning if reason == "terminal_event_lost" else logger.debug
        log(
            "ws_orphan_discarded account=%s key=%s status=%s reason=%s",
            account_id,
            key,
            status or "unknown",
            reason,
        )

    async def _apply_transition(
        self,
        order_id: UUID,
        new_state: OrderState,
        payload: dict[str, Any],
    ) -> int:
        now = datetime.now(UTC)
        if new_state == OrderState.filled:
            avg = payload.get("avgPrice") or payload.get("average")
            filled = payload.get("cumExecQty") or payload.get("filled")
            return await self._repo.transition_to_filled(
                order_id,
                exchange_order_id=str(payload.get("orderId", "")),
                filled_price=Decimal(str(avg)) if avg else None,
                filled_quantity=Decimal(str(filled)) if filled else None,
                filled_at=now,
            )
        if new_state == OrderState.rejected:
            reason = payload.get("rejectReason", "ws_rejected")
            return await self._repo.transition_to_rejected(
                order_id,
                error_message=f"ws_rejected: {reason}",
                failed_at=now,
            )
        if new_state == OrderState.cancelled:
            return await self._repo.transition_to_cancelled(order_id, cancelled_at=now)
        return 0

    async def _after_committed_winner(
        self,
        order: Order,
        new_state: OrderState,
        payload: dict[str, Any],
        account_id: UUID,
    ) -> None:
        if self._user_id is not None:
            await publish_realtime(
                str(self._user_id),
                "order_update",
                {
                    "order_id": str(order.id),
                    "state": new_state.value,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "source": "ws",
                },
            )

        if not is_native_sl(order):
            record_metric_safely(qb_active_orders.dec)
        if new_state == OrderState.filled or has_recorded_order_fill(order):
            filled = payload.get("cumExecQty") or payload.get("filled")
            filled_quantity = Decimal(str(filled)) if filled else None
            if (
                filled_quantity is not None
                and filled_quantity.is_finite()
                and filled_quantity < order.quantity
            ):
                record_partial_fill(source="ws", reduce_only=order.reduce_only)

            from src.tasks.trading import (
                _enqueue_closed_pnl_refresh,
                _enqueue_conditional_reversal_measure,
                _enqueue_trailing_if_intended,
            )

            if new_state == OrderState.filled and order.risk_context is None:
                _enqueue_trailing_if_intended(order)
            _enqueue_closed_pnl_refresh(order)
            if new_state == OrderState.filled:
                _enqueue_conditional_reversal_measure(order)
            if new_state != OrderState.rejected:
                return

        if new_state == OrderState.rejected:
            await self._alert_sender(
                self._settings,
                "Order Rejected (WS)",
                f"{order.symbol} {order.side} {order.quantity}",
                {
                    "order_id": str(order.id),
                    "account_id": str(account_id),
                    "reason": payload.get("rejectReason", "unknown"),
                },
            )

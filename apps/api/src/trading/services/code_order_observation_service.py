"""REST·WS의 증거 차이를 보존하며 Code Order와 리스크 원장을 함께 확정한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, cast
from uuid import UUID

from src.trading.models import Order, OrderState
from src.trading.providers import OrderStatusFetch, bybit_cumulative_execution_value
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_risk_service import (
    CodeRiskError,
    CodeRiskReconciliationPending,
    CodeRiskService,
    RiskCommand,
)
from src.trading.services.native_sl_observation_service import is_native_sl

_WS_TERMINAL = {
    "Filled": OrderState.filled,
    "Cancelled": OrderState.cancelled,
    "Rejected": OrderState.rejected,
    "PartiallyFilledCanceled": OrderState.cancelled,
}


@dataclass(frozen=True)
class CodeOrderObservation:
    """전송별 증거를 정규화하되 누락된 값과 실제 0을 구별한다."""

    source: Literal["ws", "rest"]
    account_id: UUID
    state: OrderState | None
    quantity: Decimal | None
    value: Decimal | None
    price: Decimal | None
    exchange_order_id: str | None
    raw: dict[str, Any]
    partial: bool = False

    @classmethod
    def from_websocket(cls, account_id: UUID, payload: dict[str, Any]) -> CodeOrderObservation:
        status = str(payload.get("orderStatus", ""))
        state = _WS_TERMINAL.get(status)
        quantity, price = None, None
        if state is not None or status == "PartiallyFilled":
            try:
                quantity = Decimal(str(payload.get("cumExecQty", payload.get("filled"))))
                if not quantity.is_finite() or quantity < 0:
                    raise ValueError("invalid fill")
            except (ValueError, InvalidOperation) as exc:
                raise CodeRiskError(
                    "코드 주문의 누적 체결 또는 리스크 귀속이 올바르지 않습니다"
                ) from exc
            average = payload.get("avgPrice") or payload.get("average")
            if state in {OrderState.cancelled, OrderState.rejected} and quantity > 0:
                try:
                    price = Decimal(str(average)) if average not in (None, "") else None
                except InvalidOperation as exc:
                    raise CodeRiskReconciliationPending(
                        "부분 체결 평균가 증거를 기다립니다"
                    ) from exc
                if price is None or not price.is_finite() or price <= 0:
                    raise CodeRiskReconciliationPending("부분 체결 평균가 증거를 기다립니다")
            elif state == OrderState.filled and average:
                price = Decimal(str(average))
        exchange_id = payload.get("orderId")
        return cls(
            "ws",
            account_id,
            state,
            quantity,
            None,
            price,
            str(exchange_id) if exchange_id else None,
            dict(payload),
            partial=status == "PartiallyFilled",
        )

    @classmethod
    def from_rest(cls, account_id: UUID, status: OrderStatusFetch) -> CodeOrderObservation:
        info = status.raw.get("info")
        native = status.raw.get("orderStatus") or (
            info.get("orderStatus") if isinstance(info, dict) else None
        )
        selected = status.status
        if native in {"PartiallyFilledCanceled", "Cancelled", "Canceled", "Deactivated"}:
            selected = "cancelled"
        elif native == "Rejected":
            selected = "rejected"
        state = OrderState(selected) if selected in {"filled", "cancelled", "rejected"} else None
        if selected == "filled" and status.filled_quantity is None:
            raise CodeRiskError("최종 체결 수량이 없습니다")
        quantity = status.filled_quantity or Decimal(0)
        if not quantity.is_finite() or quantity < 0:
            raise CodeRiskError("체결 수량이 잘못되었습니다")
        return cls(
            "rest",
            account_id,
            state,
            quantity,
            status.cumulative_value,
            status.filled_price,
            status.exchange_order_id,
            dict(status.raw),
            partial=selected == "submitted",
        )


@dataclass(frozen=True)
class CodeOrderObservationResult:
    commands: list[RiskCommand]
    state: OrderState | None = None
    transition_won: bool = False


class CodeOrderObservationService:
    def __init__(
        self,
        orders: OrderRepository,
        risk: CodeRiskService,
        *,
        risk_repo: CodeRiskRepository | None = None,
    ) -> None:
        self._orders, self._risk, self._risk_repo = orders, risk, risk_repo

    async def apply(
        self, order: Order, observation: CodeOrderObservation
    ) -> CodeOrderObservationResult:
        if order.exchange_account_id != observation.account_id:
            raise CodeRiskError("주문 계정 귀속이 올바르지 않습니다")
        ws = observation.source == "ws"
        state, quantity = observation.state, observation.quantity
        if ws and state is None and not observation.partial:
            if is_native_sl(order):
                await self._orders.commit()
            return CodeOrderObservationResult([])
        context = order.risk_context
        if context is None:
            raise CodeRiskError("주문 귀속이 없습니다")
        try:
            session_id = UUID(str(context["session_id"]))
            generation = int(str(context["generation"]))
            role = str(context["role"])
            if ws and generation < 1:
                raise ValueError("invalid generation")
        except (KeyError, ValueError) as exc:
            raise CodeRiskError(
                "코드 주문의 누적 체결 또는 리스크 귀속이 올바르지 않습니다"
            ) from exc
        assert quantity is not None
        if ws and is_native_sl(order) and observation.raw.get("_native_historical") is True:
            await self._native_pnl(order, observation)
            await self._orders.commit()
            return CodeOrderObservationResult([])
        if not ws and observation.exchange_order_id:
            await self._orders.attach_exchange_order_id(order.id, observation.exchange_order_id)
        value = Decimal(0)
        if role == "entry":
            if quantity > 0:
                observed = observation.value
                if observed is None:
                    observed = bybit_cumulative_execution_value(observation.raw)
                if observed is None:
                    raise CodeRiskReconciliationPending("진입 누적 체결대금 증거를 기다립니다")
                value = observed
            if not value.is_finite() or value < 0:
                raise CodeRiskError("코드 진입 누적 체결대금이 올바르지 않습니다")
        # REST 진입은 정확한 누적대금 증거를 먼저 기다린다. VWAP 누락이 그 대기를
        # 일반 실패로 바꾸면 executor가 재시도 대신 신규 진입을 중단한다.
        if not ws and quantity > 0 and (observation.price is None or observation.price <= 0):
            raise CodeRiskError("체결 VWAP가 없습니다")
        commands: list[RiskCommand] = []
        if role == "entry":
            commands = await self._risk.record_entry_fill(
                session_id,
                generation,
                order.id,
                cumulative_quantity=quantity,
                cumulative_value=value,
                terminal=state is not None,
                commit=False,
            )
        elif ws or quantity > 0:
            if role not in {"partial_tp", "stop_loss", "trailing_stop", "close"}:
                raise CodeRiskError("알 수 없는 코드 주문 역할입니다")
            commands = await self._risk.record_exit_fill(
                session_id,
                generation,
                order.id,
                role=cast(Literal["partial_tp", "stop_loss", "trailing_stop", "close"], role),
                cumulative_quantity=quantity,
                terminal=state is not None and (not ws or bool(observation.exchange_order_id)),
                commit=False,
            )
        if not ws:
            if role == "partial_tp" and state in {OrderState.cancelled, OrderState.rejected}:
                assert self._risk_repo is not None
                latest = (
                    await self._risk_repo.get(session_id) if quantity < order.quantity else None
                )
                if (
                    latest is not None
                    and latest.position_quantity > 0
                    and not latest.close_requested
                ):
                    await self._risk.halt(
                        session_id, generation, "partial_tp_protection_lost", commit=False
                    )
            if role == "close" and state is not None and quantity == 0:
                await self._risk.record_zero_exit(session_id, generation, order.id, commit=False)
        won = await self._transition(order, observation)
        if ws and is_native_sl(order):
            await self._native_pnl(order, observation)
        await self._orders.commit()
        return CodeOrderObservationResult(commands, state, won == 1)

    async def _transition(self, order: Order, observation: CodeOrderObservation) -> int:
        state, quantity, price = observation.state, observation.quantity, observation.price
        if state is None:
            return 0
        now = datetime.now(UTC)
        if state == OrderState.filled:
            return await self._orders.transition_to_filled(
                order.id,
                exchange_order_id=observation.exchange_order_id or "",
                filled_price=price,
                filled_quantity=quantity,
                filled_at=now,
            )
        if observation.source == "ws" and observation.exchange_order_id:
            await self._orders.attach_exchange_order_id(order.id, observation.exchange_order_id)
        if state == OrderState.cancelled:
            return await self._orders.transition_to_cancelled(
                order.id,
                cancelled_at=now,
                filled_quantity=quantity,
                filled_price=price,
            )
        reason = (
            f"ws_rejected: {observation.raw.get('rejectReason', 'ws_rejected')}"
            if observation.source == "ws"
            else "code_policy_rejected"
        )
        return await self._orders.transition_to_rejected(
            order.id,
            error_message=reason,
            failed_at=now,
            filled_quantity=quantity,
            filled_price=price,
        )

    async def _native_pnl(self, order: Order, observation: CodeOrderObservation) -> None:
        quantity = observation.quantity
        raw = observation.raw.get("closedPnl")
        if observation.state is None or quantity is None or quantity <= 0 or raw in (None, ""):
            return
        try:
            pnl = Decimal(str(raw))
        except InvalidOperation as exc:
            raise CodeRiskReconciliationPending("native SL 손익 증거를 기다립니다") from exc
        if not pnl.is_finite():
            raise CodeRiskReconciliationPending("native SL 손익이 유한하지 않습니다")
        if order.realized_pnl_synced_at is not None and order.realized_pnl != pnl:
            raise CodeRiskReconciliationPending("native SL의 확정 손익 증거가 다릅니다")
        await self._orders.record_native_sl_pnl(order, quantity=quantity, pnl=pnl)

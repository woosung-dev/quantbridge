"""명시적인 Bybit attached SL 부모만 관측 주문에 귀속한다. commit은 호출자가 소유한다."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from src.market_data.constants import to_bybit_raw_symbol
from src.trading.models import ExchangeMode, ExchangeName, Order, OrderSide, OrderState, OrderType
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_risk_service import CodeRiskError, CodeRiskReconciliationPending

NATIVE_SL_ORIGIN = "bybit_attached_sl"


def is_native_sl(order: Order) -> bool:
    return (order.risk_context or {}).get("native_origin") == NATIVE_SL_ORIGIN


class NativeSLParentPending(CodeRiskReconciliationPending):
    def __init__(self, session_id: UUID, generation: int) -> None:
        super().__init__("부모 진입의 최종 체결 증거를 기다립니다")
        self.session_id, self.generation = session_id, generation


class NativeSLObservationService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def bind(
        self, account_id: UUID, payload: dict[str, Any]
    ) -> tuple[Order, dict[str, Any]] | None:
        """락·관측 행·정확한 대금만 준비한다. 같은 TX에서 체결 CAS 후 commit해야 한다."""
        try:
            parent_id = UUID(str(payload.get("parentOrderLinkId", "")))
        except ValueError:
            return None
        external_id = payload.get("orderId")
        if (
            not isinstance(external_id, str)
            or not external_id
            or len(external_id) > 120
            or payload.get("category") != "linear"
            or payload.get("stopOrderType") != "StopLoss"
            or payload.get("createType") != "CreateByStopLoss"
            or payload.get("reduceOnly") is not True
            or type(payload.get("positionIdx")) is not int
            or payload["positionIdx"] != 0
        ):
            return None
        key = f"native-sl:{account_id}:{external_id}"
        await self._repo.acquire_idempotency_lock(key)
        identity = {
            k: payload.get(k)
            for k in (
                "parentOrderLinkId",
                "orderId",
                "category",
                "symbol",
                "side",
                "positionIdx",
                "reduceOnly",
                "stopOrderType",
                "createType",
            )
        }
        existing = await self._repo.get_by_exchange_order_id(external_id, account_id=account_id)
        bound = await self._repo.native_sl_parent(parent_id, account_id)
        if bound is None:
            # 이미 증명한 과거 세대는 Order/PnL만 보충한다. 현재 risk 원장은 건드리지 않는다.
            if existing is None or not is_native_sl(existing):
                return None
            old = existing.risk_context or {}
            parent = await self._repo.get_by_id(parent_id)
            parent_context = parent.risk_context if parent is not None else None
            if (
                parent is None
                or parent.exchange_account_id != account_id
                or parent_context is None
                or parent_context.get("role") != "entry"
                or old.get("parent_order_id") != str(parent_id)
                or old.get("session_id") != parent_context.get("session_id")
                or old.get("generation") != parent_context.get("generation")
                or old.get("native_binding") != identity
                or old.get("role") != "stop_loss"
                or existing.symbol != parent.symbol
                or not existing.reduce_only
                or existing.side
                != (OrderSide.sell if parent.side == OrderSide.buy else OrderSide.buy)
                or existing.state
                not in {OrderState.filled, OrderState.cancelled, OrderState.rejected}
            ):
                raise CodeRiskError("과거 native SL의 명시 귀속이 다릅니다")
            evidence = old.get("native_fill")
            try:
                if not isinstance(evidence, dict):
                    raise ValueError("missing evidence")
                quantity, value = (
                    Decimal(str(evidence["quantity"])),
                    Decimal(str(evidence["value"])),
                )
                if (
                    not quantity.is_finite()
                    or not value.is_finite()
                    or quantity <= 0
                    or value <= 0
                    or Decimal(str(payload.get("cumExecQty"))) != quantity
                    or Decimal(str(payload.get("cumExecValue"))) != value
                ):
                    raise ValueError("different evidence")
            except (ValueError, InvalidOperation, KeyError) as exc:
                raise CodeRiskReconciliationPending(
                    "과거 native SL의 확정 누적 증거가 다릅니다"
                ) from exc
            return existing, {
                **payload,
                "avgPrice": str(value / quantity),
                "_native_historical": True,
            }
        parent, session, risk, account = bound
        context = parent.risk_context or {}
        if (
            account.exchange != ExchangeName.bybit
            or account.mode != ExchangeMode.demo
            or (session.execution_snapshot or {}).get("source_policy") != "code_v1"
            or parent.reduce_only
            or parent.stop_loss is None
            or parent.stop_loss <= 0
            or parent.exchange_order_id == external_id
            or context.get("role") != "entry"
            or context.get("session_id") != str(session.id)
            or context.get("generation") != risk.generation
            or payload.get("symbol") != to_bybit_raw_symbol(session.symbol)
            or payload.get("side") != ("Sell" if parent.side == OrderSide.buy else "Buy")
            or (parent.side == OrderSide.buy) != (risk.direction == "long")
        ):
            return None
        try:
            quantity = Decimal(str(payload.get("qty")))
            filled = Decimal(str(payload.get("cumExecQty")))
            value = Decimal(str(payload.get("cumExecValue")))
            if (
                not all(v.is_finite() for v in (quantity, filled, value))
                or quantity <= 0
                or quantity > risk.expected_quantity
                or filled < 0
                or filled > quantity
                or value < 0
                or (filled > 0 and value <= 0)
                or (filled == 0 and value != 0)
            ):
                raise ValueError("invalid cumulative execution")
        except (InvalidOperation, ValueError) as exc:
            raise CodeRiskReconciliationPending(
                "native SL의 정확한 누적 체결 증거를 기다립니다"
            ) from exc
        if not risk.entry_terminal and filled == 0:
            return None
        if (
            not risk.entry_terminal
            or risk.cumulative_quantity <= 0
            or filled > risk.cumulative_quantity
        ):
            raise NativeSLParentPending(session.id, risk.generation)
        identifier = uuid5(NAMESPACE_URL, key)
        order = existing
        evidence = {"quantity": str(filled), "value": str(value)}
        if order is not None:
            old = order.risk_context or {}
            if (
                order.id != identifier
                or not is_native_sl(order)
                or old.get("session_id") != str(session.id)
                or old.get("generation") != risk.generation
                or old.get("parent_order_id") != str(parent.id)
                or old.get("native_binding") != identity
                or old.get("role") != "stop_loss"
                or order.symbol != session.symbol
                or not order.reduce_only
                or order.side != (OrderSide.sell if parent.side == OrderSide.buy else OrderSide.buy)
            ):
                raise CodeRiskError("native SL의 기존 귀속이 다릅니다")
            previous = old.get("native_fill", {})
            if isinstance(previous, dict):
                old_qty = Decimal(str(previous.get("quantity", "0")))
                old_value = Decimal(str(previous.get("value", "0")))
                if filled < old_qty:
                    raise CodeRiskReconciliationPending("native SL의 이전 누적 응답을 보류합니다")
                if (filled == old_qty and value != old_value) or value < old_value:
                    raise CodeRiskReconciliationPending("native SL의 누적 대금이 일치하지 않습니다")
            order.risk_context = {**old, "native_fill": evidence}
        else:
            order = Order(
                id=identifier,
                strategy_id=parent.strategy_id,
                exchange_account_id=account_id,
                symbol=session.symbol,
                side=OrderSide.sell if parent.side == OrderSide.buy else OrderSide.buy,
                type=OrderType.market,
                quantity=quantity,
                state=OrderState.submitted,
                submitted_at=datetime.now(UTC),
                exchange_order_id=external_id,
                reduce_only=True,
                leverage=parent.leverage,
                margin_mode=parent.margin_mode,
                idempotency_key=key,
                risk_context={
                    "session_id": str(session.id),
                    "generation": risk.generation,
                    "role": "stop_loss",
                    "native_origin": NATIVE_SL_ORIGIN,
                    "parent_order_id": str(parent.id),
                    "native_binding": identity,
                    "native_fill": evidence,
                },
            )
        if filled > 0:
            order.filled_quantity = filled
            order.filled_price = value / filled
        await self._repo.save(order)
        canonical = dict(payload)
        canonical.pop("_native_historical", None)
        if filled > 0:
            canonical["avgPrice"] = str(value / filled)
        return order, canonical

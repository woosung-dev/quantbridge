"""새 정책 전용 Bybit demo 어댑터. 기존 주문 경로를 바꾸지 않는다."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from src.trading.models import (
    CodeRiskCommand,
    LiveRiskState,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import BybitFuturesProvider, Credentials, OrderStatusFetch, OrderSubmit
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.code_risk_service import CodeRiskError, CodeRiskService


class BybitCodeRiskVenue:
    def __init__(
        self,
        repo: CodeRiskRepository,
        orders: OrderRepository,
        risk: CodeRiskService,
        accounts: ExchangeAccountService,
        provider: BybitFuturesProvider,
    ) -> None:
        self._repo, self._orders, self._risk, self._accounts, self._provider = (
            repo,
            orders,
            risk,
            accounts,
            provider,
        )

    async def _creds(self, session: LiveSignalSession) -> Credentials:
        return await self._accounts.get_credentials_for_order(session.exchange_account_id)

    async def reconcile(self, session: LiveSignalSession, state: LiveRiskState) -> None:
        creds = await self._creds(session)
        orders = await self._repo.child_orders(session.id, state.generation)
        entry = await self._repo.get_order(state.entry_order_id)
        if entry is not None:
            orders.append(entry)
        for order in orders:
            if order.state != OrderState.pending:
                status = await self._provider.fetch_order_by_client_id(
                    creds, str(order.id), order.symbol
                )
                if status is not None:
                    await self._sync(order, status)
        latest = await self._repo.get(session.id)
        if latest is not None and latest.entry_terminal and latest.position_quantity > 0:
            position = await self._provider.fetch_position(creds, session.symbol)
            if position is None:
                await self._risk.confirm_flat_and_cancelled(
                    session.id, latest.generation, flat=True, cancelled=False
                )
            elif position.side != latest.direction or position.size > latest.position_quantity:
                await self._risk.halt(session.id, latest.generation, "position_ledger_mismatch")
            elif position.size < latest.position_quantity:
                identifier = uuid5(
                    NAMESPACE_URL, f"risk:{session.id}:{latest.generation}:native_exit"
                )
                previous = Decimal(str(latest.exit_fills.get(str(identifier), 0)))
                await self._risk.record_exit_fill(
                    session.id,
                    latest.generation,
                    order_id=identifier,
                    role="stop_loss",
                    cumulative_quantity=previous + latest.position_quantity - position.size,
                )

    async def execute(
        self, command: CodeRiskCommand, session: LiveSignalSession, state: LiveRiskState
    ) -> dict[str, Any]:
        creds = await self._creds(session)
        if command.kind == "submit_entry":
            entry = await self._repo.get_order(state.entry_order_id)
            if (
                entry is None
                or entry.leverage is None
                or entry.margin_mode not in {"cross", "isolated"}
            ):
                raise CodeRiskError("linear 진입 주문 설정이 없습니다")
            if entry.stop_loss != state.provisional_stop:
                raise CodeRiskError("임시 보호 SL이 주문에 없습니다")
            return await self._submit(creds, entry)
        if command.kind == "cancel_entry":
            entry = await self._repo.get_order(state.entry_order_id)
            if entry is None:
                raise CodeRiskError("진입 주문이 없습니다")
            await self._cancel_confirm(creds, entry)
            return {"cancel_confirmed": True}
        if command.kind == "flatten":
            position = await self._provider.fetch_position(creds, session.symbol)
            if position is None or position.size == 0:
                await self._risk.confirm_flat_and_cancelled(
                    session.id, state.generation, flat=True, cancelled=False
                )
                return {"flat": True}
            if position.side != state.direction:
                raise CodeRiskError("포지션 방향이 원장과 다릅니다")
            child = await self._child(
                session,
                state,
                command.key,
                "close",
                min(position.size, Decimal(str(command.payload["quantity"]))),
            )
            return await self._submit(creds, child)
        if command.kind == "apply_protection":
            position = await self._provider.fetch_position(creds, session.symbol)
            if (
                position is None
                or position.side != state.direction
                or position.size != state.position_quantity
            ):
                raise CodeRiskError("보호 적용 시 포지션과 원장이 다릅니다")
            p = command.payload
            native_needed = (
                "trailing_distance" in p
                and state.protection_applied.get("trailing_distance") != p["trailing_distance"]
            )
            await self._provider.set_code_protection(
                creds,
                symbol=session.symbol,
                stop_loss=Decimal(str(p["stop_loss"])),
                distance=Decimal(str(p["trailing_distance"])) if native_needed else None,
                active_price=Decimal(str(p["trailing_activation"])) if native_needed else None,
            )
            # 절반 TP는 영속 Order로 별도 제출해 체결 누적·WS 귀속을 보존한다.
            tp_qty = Decimal(str(p.get("tp_quantity", 0)))
            if tp_qty > 0:
                child = await self._child(
                    session,
                    state,
                    f"risk:{session.id}:{state.generation}:partial_tp",
                    "partial_tp",
                    tp_qty,
                    Decimal(str(p["tp_price"])),
                )
                await self._submit(creds, child)
            return {"accepted": True, "token": p["token"]}
        if command.kind == "cancel_children":
            for child in await self._repo.child_orders(session.id, state.generation):
                await self._cancel_confirm(creds, child)
            position = await self._provider.fetch_position(creds, session.symbol)
            # 거래소가 생성한 보호 자식도 없어야 반전할 수 있다.
            pending = await self._provider.fetch_open_conditional_orders(creds, session.symbol)
            if position is not None or pending:
                raise CodeRiskError("flat·보호 자식 취소 확인을 기다립니다")
            await self._risk.confirm_flat_and_cancelled(
                session.id, state.generation, flat=True, cancelled=True
            )
            return {"flat": True, "cancel_confirmed": True}
        raise CodeRiskError("지원하지 않는 리스크 명령입니다")

    async def _child(
        self,
        session: LiveSignalSession,
        state: LiveRiskState,
        key: str,
        role: str,
        quantity: Decimal,
        price: Decimal | None = None,
    ) -> Order:
        identifier = uuid5(NAMESPACE_URL, key)
        existing = await self._repo.get_order(identifier)
        if existing is not None:
            return existing
        entry = await self._repo.get_order(state.entry_order_id)
        if entry is None:
            raise CodeRiskError("진입 주문 설정이 없습니다")
        order = Order(
            id=identifier,
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
            side=OrderSide.sell if state.direction == "long" else OrderSide.buy,
            type=OrderType.limit if price is not None else OrderType.market,
            quantity=quantity,
            price=price,
            state=OrderState.pending,
            reduce_only=True,
            leverage=entry.leverage,
            margin_mode=entry.margin_mode,
            idempotency_key=str(identifier),
            risk_context={
                "session_id": str(session.id),
                "generation": state.generation,
                "role": role,
            },
        )
        await self._orders.save(order)
        await self._repo.commit()
        return order

    async def _submit(self, creds: Credentials, order: Order) -> dict[str, Any]:
        # UUID가 주문 id이자 Bybit orderLinkId다. 응답 유실 후 생성보다 조회가 먼저다.
        status = await self._provider.fetch_order_by_client_id(creds, str(order.id), order.symbol)
        if status is None:
            if order.state not in {OrderState.pending, OrderState.submitted}:
                return {"order_id": str(order.id), "terminal": True}
            await self._orders.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
            await self._repo.commit()
            receipt = await self._provider.create_order(
                creds,
                OrderSubmit(
                    symbol=order.symbol,
                    side=order.side,
                    type=order.type,
                    quantity=order.quantity,
                    price=order.price,
                    leverage=order.leverage,
                    margin_mode=cast(Literal["cross", "isolated"], order.margin_mode),
                    client_order_id=str(order.id),
                    reduce_only=order.reduce_only,
                    stop_loss=order.stop_loss,
                ),
            )
            status = OrderStatusFetch(
                exchange_order_id=receipt.exchange_order_id,
                status=receipt.status,
                filled_price=receipt.filled_price,
                filled_quantity=receipt.filled_quantity,
                raw=receipt.raw,
            )
        await self._orders.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
        await self._orders.attach_exchange_order_id(order.id, status.exchange_order_id)
        await self._repo.commit()
        await self._sync(order, status)
        if status.status == "rejected" or (
            status.status == "cancelled"
            and order.risk_context is not None
            and order.risk_context.get("role") == "partial_tp"
            and (status.filled_quantity or Decimal(0)) < order.quantity
        ):
            raise CodeRiskError("거래소가 주문을 거부했습니다")
        return {
            "order_id": str(order.id),
            "exchange_order_id": status.exchange_order_id,
            "status": status.status,
        }

    async def _sync(self, order: Order, status: OrderStatusFetch) -> None:
        context = order.risk_context
        if context is None:
            raise CodeRiskError("주문 귀속이 없습니다")
        await self._orders.attach_exchange_order_id(order.id, status.exchange_order_id)
        terminal = status.status in {"filled", "cancelled", "rejected"}
        if status.status == "filled" and status.filled_quantity is None:
            raise CodeRiskError("최종 체결 수량이 없습니다")
        quantity = status.filled_quantity or Decimal(0)
        if not quantity.is_finite() or quantity < 0:
            raise CodeRiskError("체결 수량이 잘못되었습니다")
        if quantity > 0 and (status.filled_price is None or status.filled_price <= 0):
            raise CodeRiskError("체결 VWAP가 없습니다")
        session_id, generation = UUID(str(context["session_id"])), int(str(context["generation"]))
        if context["role"] == "entry":
            info = status.raw.get("info")
            raw_value = info.get("cumExecValue") if isinstance(info, dict) else None
            cumulative_value = (
                Decimal(str(raw_value))
                if raw_value not in (None, "")
                else quantity * (status.filled_price or Decimal(0))
            )
            await self._risk.record_entry_fill(
                session_id,
                generation,
                order.id,
                cumulative_quantity=quantity,
                cumulative_value=cumulative_value,
                terminal=terminal,
                commit=False,
            )
        elif quantity > 0:
            await self._risk.record_exit_fill(
                session_id,
                generation,
                order_id=order.id,
                role=cast(Any, context["role"]),
                cumulative_quantity=quantity,
                commit=False,
            )
        if (
            context["role"] == "partial_tp"
            and status.status in {"cancelled", "rejected"}
            and quantity < order.quantity
        ):
            latest = await self._repo.get(session_id)
            if latest is not None and latest.position_quantity > 0 and not latest.close_requested:
                await self._risk.halt(
                    session_id, generation, "partial_tp_protection_lost", commit=False
                )
        if context["role"] == "close" and terminal and quantity == 0:
            await self._risk.record_zero_exit(session_id, generation, order.id, commit=False)
        if status.status == "filled":
            await self._orders.transition_to_filled(
                order.id,
                exchange_order_id=status.exchange_order_id,
                filled_price=status.filled_price,
                filled_quantity=quantity,
                filled_at=datetime.now(UTC),
            )
        elif status.status == "cancelled":
            await self._orders.transition_to_cancelled(
                order.id,
                cancelled_at=datetime.now(UTC),
                filled_price=status.filled_price,
                filled_quantity=quantity,
            )
        elif status.status == "rejected":
            await self._orders.transition_to_rejected(
                order.id,
                error_message="code_policy_rejected",
                failed_at=datetime.now(UTC),
                filled_price=status.filled_price,
                filled_quantity=quantity,
            )
        await self._repo.commit()

    async def _cancel_confirm(self, creds: Credentials, order: Order) -> None:
        if order.state in {OrderState.filled, OrderState.cancelled, OrderState.rejected}:
            return
        if order.state == OrderState.pending and order.exchange_order_id is None:
            await self._orders.transition_pending_to_cancelled(
                order.id, cancelled_at=datetime.now(UTC)
            )
            if order.risk_context and order.risk_context.get("role") == "entry":
                await self._risk.record_entry_fill(
                    UUID(str(order.risk_context["session_id"])),
                    int(str(order.risk_context["generation"])),
                    order.id,
                    cumulative_quantity=Decimal(0),
                    cumulative_value=Decimal(0),
                    terminal=True,
                    commit=False,
                )
            await self._repo.commit()
            return
        status = await self._provider.fetch_order_by_client_id(creds, str(order.id), order.symbol)
        if status is None:
            # 검색 지연·응답 유실은 미발주 증거가 아니므로 취소 성공으로 간주하지 않는다.
            raise CodeRiskError("취소 대상의 거래소 상태를 확인할 수 없습니다")
        if status.status == "submitted":
            await self._provider.cancel_order(creds, status.exchange_order_id, order.symbol)
            status = await self._provider.fetch_order(creds, status.exchange_order_id, order.symbol)
        if status.status == "submitted":
            raise CodeRiskError("거래소 취소 확정을 기다립니다")
        await self._sync(order, status)

"""동결된 코드 신호를 공통 리스크·영속 주문 실행기로 넘긴다."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from src.strategy.python_runtime.swing_risk import Direction
from src.trading.code_execution_snapshot import validate_code_snapshot
from src.trading.models import Order, OrderSide, OrderState, OrderType
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_risk_executor import CodeRiskExecutor
from src.trading.services.code_risk_service import CodeRiskError, CodeRiskService


class CodeLiveExecutionService:
    def __init__(
        self,
        repo: CodeRiskRepository,
        orders: OrderRepository,
        risk: CodeRiskService,
        executor: CodeRiskExecutor,
        *,
        entry_gate: Callable[[UUID, UUID], Awaitable[None]],
    ) -> None:
        self._repo, self._orders, self._risk, self._executor, self._entry_gate = (
            repo,
            orders,
            risk,
            executor,
            entry_gate,
        )

    async def on_intent(
        self,
        session_id: UUID,
        action: Literal["hold", "long", "short", "close"],
        *,
        intent_key: str | None = None,
        estimated_entry: Decimal | None = None,
        quantity: Decimal | None = None,
        previous_bars: Sequence[Mapping[str, Decimal]] | None = None,
        qty_step: Decimal | None = None,
        min_qty: Decimal | None = None,
    ) -> None:
        session = await self._repo.get_session(session_id)
        if session is None or session.execution_snapshot is None:
            raise CodeRiskError("code_v1 세션이 아닙니다")
        await self._executor.drain(session_id)
        state = await self._repo.get(session_id)
        if state is not None and (state.position_quantity > 0 or not state.entry_terminal):
            await self._risk.request_signal(session_id, state.generation, action)
            if estimated_entry is not None:
                await self._risk.mark_price(session_id, state.generation, estimated_entry)
            await self._executor.drain(session_id)
            return
        if action in {"hold", "close"}:
            return
        if state is not None and (
            state.new_entries_blocked
            or not state.cancels_confirmed
            or state.pending_reversal not in (None, action)
        ):
            return
        if not session.is_active:
            raise CodeRiskError("종료된 세션입니다")
        account = await self._repo.get_account(session.exchange_account_id)
        version = (
            await self._repo.get_version(session.strategy_version_id)
            if session.strategy_version_id
            else None
        )
        if account is None:
            raise CodeRiskError("세션 계정이 없습니다")
        snapshot = validate_code_snapshot(
            session.execution_snapshot,
            version=version,
            version_id=session.strategy_version_id,
            account=account,
        )
        settings = snapshot.get("execution_settings")
        if (
            not isinstance(settings, dict)
            or type(settings.get("leverage")) is not int
            or settings["leverage"] < 1
            or settings.get("margin_mode") not in {"cross", "isolated"}
        ):
            raise CodeRiskError("동결된 linear 실행 설정이 없습니다")
        if (
            estimated_entry is None
            or quantity is None
            or previous_bars is None
            or qty_step is None
            or min_qty is None
        ):
            raise CodeRiskError("새 진입에는 수량·최근 완료 2봉·거래소 수량 규칙이 필요합니다")
        if not intent_key:
            raise CodeRiskError("새 진입에는 세션·봉에 고정된 의도 멱등키가 필요합니다")
        identifier = uuid5(NAMESPACE_URL, f"code-entry:{session.id}:{intent_key}")
        # 체크포인트 delivered ACK 유실 뒤 이미 종료된 같은 봉도 재진입하지 않는다.
        if await self._repo.get_order(identifier) is not None:
            return
        await self._entry_gate(session.strategy_id, session.exchange_account_id)
        order = Order(
            id=identifier,
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
            side=OrderSide.buy if action == "long" else OrderSide.sell,
            type=OrderType.market,
            quantity=quantity,
            state=OrderState.pending,
            leverage=settings["leverage"],
            margin_mode=settings["margin_mode"],
        )
        await self._orders.save(order)
        # prepare_entry가 주문·임시 SL·원장·outbox를 같은 트랜잭션으로 확정한다.
        direction: Direction = "long" if action == "long" else "short"
        await self._risk.prepare_entry(
            session_id,
            order.id,
            direction=direction,
            estimated_entry=estimated_entry,
            quantity=quantity,
            previous_bars=previous_bars,
            qty_step=qty_step,
            min_qty=min_qty,
        )
        await self._executor.drain(session_id)

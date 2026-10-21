"""거래소 호출 없이 영속 리스크 전이와 재시도 가능한 명령만 반환한다."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal, cast
from uuid import UUID

from src.strategy.python_runtime.swing_risk import POLICY, Direction, RiskPlan, create_plan
from src.trading.models import CodeRiskCommand, LiveRiskState, OrderSide, OrderState
from src.trading.repositories.code_risk_repository import CodeRiskRepository

ZERO = Decimal(0)
PRICE_QUANTUM = Decimal("0.00000001")  # 주문·리스크 원장의 NUMERIC(..., 8)과 같은 정밀도다.


class CodeRiskError(ValueError):
    """부정확한 체결이나 경쟁 갱신을 성공으로 보고하지 않는다."""


@dataclass(frozen=True)
class RiskCommand:
    kind: str
    key: str
    payload: dict[str, object]


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise CodeRiskError(f"{name}은 유한한 양수 Decimal이어야 합니다")


class CodeRiskService:
    def __init__(self, repo: CodeRiskRepository) -> None:
        self._repo = repo

    async def prepare_entry(
        self,
        session_id: UUID,
        entry_order_id: UUID,
        *,
        direction: Direction,
        estimated_entry: Decimal,
        quantity: Decimal,
        previous_bars: Sequence[Mapping[str, Decimal]],
        qty_step: Decimal,
        min_qty: Decimal,
    ) -> list[RiskCommand]:
        """발주 전 임시 SL·세대·귀속을 주문과 원장에 함께 commit한다."""
        for value, name in ((quantity, "수량"), (qty_step, "수량 단위"), (min_qty, "최소 수량")):
            _positive(value, name)
        half = quantity * POLICY.partial_fraction
        if half < min_qty or half % qty_step != 0:
            raise CodeRiskError("절반 수량이 거래소 최소 수량·단위를 만족하지 않습니다")
        current = await self._repo.get(session_id)
        if current is not None and (
            current.new_entries_blocked
            or current.position_quantity > 0
            or not current.entry_terminal
            or not current.cancels_confirmed
            or current.entry_order_id == entry_order_id
        ):
            raise CodeRiskError("기존 진입·포지션·보호 취소가 끝나기 전 새 진입은 불가합니다")
        if current is not None and current.pending_reversal not in (None, direction):
            raise CodeRiskError("확정된 반전 의도와 새 진입 방향이 다릅니다")
        order = await self._repo.get_entry_order(session_id, entry_order_id)
        side = OrderSide.buy if direction == "long" else OrderSide.sell
        if (
            order is None
            or order.state != OrderState.pending
            or order.side != side
            or order.quantity != quantity
            or order.reduce_only
        ):
            raise CodeRiskError("세션에 귀속된 같은 방향·수량의 미발주 진입 주문이 필요합니다")
        generation = current.generation + 1 if current is not None else 1
        provisional = create_plan(
            entry_price=estimated_entry,
            qty=quantity,
            direction=direction,
            previous_bars=previous_bars,
            generation=generation,
        )
        state = LiveRiskState(
            session_id=session_id,
            generation=generation,
            direction=direction,
            entry_order_id=entry_order_id,
            expected_quantity=quantity,
            reference_bars=[
                {key: str(bar[key]) for key in ("low", "high")} for bar in previous_bars
            ],
            qty_step=qty_step,
            min_qty=min_qty,
            provisional_stop=provisional.stop_loss,
        )
        saved = (
            await self._repo.create_if_absent(state)
            if current is None
            else await self._repo.compare_and_swap(state, current.revision)
        )
        if not saved:
            raise CodeRiskError("리스크 원장 CAS 충돌: 재조회가 필요합니다")
        if not await self._repo.attach_entry(state, provisional.stop_loss):
            await self._repo.rollback()
            raise CodeRiskError("발주 전 주문 귀속 경쟁: 임시 SL을 저장하지 못했습니다")
        commands = self._commands(state)
        await self._enqueue(state, commands)
        await self._repo.commit()
        return commands

    async def record_entry_fill(
        self,
        session_id: UUID,
        generation: int,
        entry_order_id: UUID,
        *,
        cumulative_quantity: Decimal,
        cumulative_value: Decimal,
        terminal: bool,
        commit: bool = True,
    ) -> list[RiskCommand]:
        """누적 체결은 단조 증가하며 terminal VWAP만 초기 R을 확정한다."""
        state = await self._load(session_id, generation)
        if state is None or state.entry_order_id != entry_order_id:
            return []
        for value in (cumulative_quantity, cumulative_value):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CodeRiskError("누적 체결은 유한한 음이 아닌 Decimal이어야 합니다")
        if cumulative_quantity < state.cumulative_quantity:
            return []
        if (
            cumulative_quantity == state.cumulative_quantity
            and cumulative_value == state.cumulative_value
            and (not terminal or state.entry_terminal)
        ):
            return []
        old_quantity, old_value = state.cumulative_quantity, state.cumulative_value
        state.position_quantity += cumulative_quantity - old_quantity
        state.cumulative_quantity = cumulative_quantity
        state.cumulative_value = cumulative_value
        if cumulative_quantity > 0:
            state.entry_vwap = (cumulative_value / cumulative_quantity).quantize(PRICE_QUANTUM)
        if (
            cumulative_quantity > state.expected_quantity
            or (cumulative_quantity == old_quantity and cumulative_value != old_value)
            or cumulative_value < old_value
            or (cumulative_quantity > 0 and cumulative_value <= 0)
            or (state.entry_terminal and cumulative_quantity > old_quantity)
        ):
            return await self._fail(state, "conflicting_cumulative_entry_fill", commit=commit)
        state.entry_terminal = state.entry_terminal or terminal
        sign = Decimal(1) if state.direction == "long" else Decimal(-1)
        if (
            not state.entry_terminal
            and state.entry_vwap is not None
            and sign * (state.entry_vwap - state.provisional_stop) <= 0
        ):
            return await self._fail(state, "partial_fill_invalid_provisional_stop", commit=commit)
        if state.entry_terminal and state.cumulative_quantity > 0:
            half = state.cumulative_quantity * POLICY.partial_fraction
            if half < state.min_qty or half % state.qty_step != 0:
                return await self._fail(state, "terminal_partial_fill_cannot_split", commit=commit)
            try:
                plan = self._plan(state)
            except ValueError:
                return await self._fail(state, "terminal_fill_invalid_risk_distance", commit=commit)
            if state.fixed_r is not None and state.fixed_r != plan.risk:
                return await self._fail(state, "terminal_fill_changed_fixed_r", commit=commit)
            state.fixed_r = plan.risk.quantize(PRICE_QUANTUM)
            if state.fixed_r <= 0:
                return await self._fail(state, "terminal_fill_invalid_risk_distance", commit=commit)
        if state.position_quantity > 0:
            self._desire_protection(state)
        return await self._save(state, commit=commit)

    async def acknowledge_protection(
        self,
        session_id: UUID,
        generation: int,
        *,
        token: str,
        success: bool,
    ) -> list[RiskCommand]:
        state = await self._load(session_id, generation)
        if state is None or state.protection_desired.get("token") != token:
            return []
        if not success:
            return await self._fail(state, "protection_ack_failed")
        if state.protection_applied == state.protection_desired:
            return []
        state.protection_applied = dict(state.protection_desired)
        return await self._save(state)

    async def request_signal(
        self,
        session_id: UUID,
        generation: int,
        action: Literal["hold", "long", "short", "close"],
    ) -> list[RiskCommand]:
        state = await self._load(session_id, generation)
        if state is None or action == "hold" or action == state.direction:
            return []
        if action not in ("long", "short", "close"):
            raise CodeRiskError("알 수 없는 신호입니다")
        state.close_requested = True
        state.pending_reversal = action if action in ("long", "short") else None
        return await self._save(state)

    async def record_exit_fill(
        self,
        session_id: UUID,
        generation: int,
        order_id: UUID,
        *,
        role: Literal["partial_tp", "stop_loss", "trailing_stop", "close"],
        cumulative_quantity: Decimal,
        commit: bool = True,
    ) -> list[RiskCommand]:
        state = await self._load(session_id, generation)
        if state is None:
            return []
        if role not in ("partial_tp", "stop_loss", "trailing_stop", "close"):
            raise CodeRiskError("알 수 없는 청산 역할입니다")
        if (
            not isinstance(cumulative_quantity, Decimal)
            or not cumulative_quantity.is_finite()
            or cumulative_quantity < 0
        ):
            raise CodeRiskError("청산 누적 수량은 유한한 음이 아닌 Decimal이어야 합니다")
        prior = state.exit_fills.get(str(order_id))
        prior_qty = Decimal(str(prior["quantity"])) if isinstance(prior, dict) else ZERO
        if isinstance(prior, dict) and prior.get("role") != role:
            return await self._fail(state, "exit_order_changed_role", commit=commit)
        if cumulative_quantity <= prior_qty:
            return []
        delta = cumulative_quantity - prior_qty
        state.exit_fills = {
            **state.exit_fills,
            str(order_id): {"quantity": str(cumulative_quantity), "role": role},
        }
        remaining = state.position_quantity
        state.position_quantity = max(ZERO, remaining - delta)
        if role == "partial_tp":
            state.tp_filled_quantity += delta
        else:
            state.close_requested = True
        if (
            delta > remaining
            or state.tp_filled_quantity > state.cumulative_quantity * POLICY.partial_fraction
        ):
            return await self._fail(
                state, "exit_fill_exceeds_position_or_partial_target", commit=commit
            )
        if state.position_quantity > 0:
            self._desire_protection(state)
        else:
            state.cancels_confirmed = False
        return await self._save(state, commit=commit)

    async def record_zero_exit(
        self, session_id: UUID, generation: int, order_id: UUID, *, commit: bool = True
    ) -> list[RiskCommand]:
        """체결 없이 종결된 청산 시도를 기록해 다음 시도의 UUID를 바꾼다."""
        state = await self._load(session_id, generation)
        if state is None or str(order_id) in state.exit_fills:
            return []
        state.exit_fills = {**state.exit_fills, str(order_id): "0"}
        return await self._save(state, commit=commit)

    async def mark_price(
        self, session_id: UUID, generation: int, price: Decimal
    ) -> list[RiskCommand]:
        """실제 가격 관측으로 보호 의도만 이동한다. 가상 체결을 만들지 않는다."""
        _positive(price, "가격")
        state = await self._load(session_id, generation)
        if (
            state is None
            or state.fixed_r is None
            or state.position_quantity <= 0
            or state.close_requested
        ):
            return []
        plan = self._plan(state)
        sign = Decimal(1) if state.direction == "long" else Decimal(-1)
        if not state.trailing_active and sign * (price - plan.trailing_activation) < 0:
            return []
        state.trailing_active = True
        old_stop = Decimal(str(state.protection_desired["stop_loss"]))
        proposed = price - sign * plan.trailing_distance
        stop = (
            max(old_stop, plan.entry_price, proposed)
            if sign > 0
            else min(old_stop, plan.entry_price, proposed)
        )
        if stop == old_stop and state.protection_desired.get("trailing_active") is True:
            return []
        self._desire_protection(state, stop=stop)
        return await self._save(state)

    async def confirm_flat_and_cancelled(
        self,
        session_id: UUID,
        generation: int,
        *,
        flat: bool,
        cancelled: bool,
    ) -> list[RiskCommand]:
        """거래소 flat 관측과 자식 주문 취소 ACK가 함께 있어야 반전을 허용한다."""
        state = await self._load(session_id, generation)
        if state is None:
            return []
        if flat:
            state.position_quantity = ZERO
        state.cancels_confirmed = flat and cancelled and state.entry_terminal
        return await self._save(state)

    async def recover(self, session_id: UUID) -> list[RiskCommand]:
        state = await self._repo.get(session_id)
        return self._commands(state) if state is not None else []

    async def stop_session(self, session_id: UUID) -> list[RiskCommand]:
        state = await self._repo.get(session_id)
        if state is None:
            return []
        return await self.request_signal(session_id, state.generation, "close")

    async def halt(self, session_id: UUID, generation: int, reason: str) -> list[RiskCommand]:
        state = await self._load(session_id, generation)
        return await self._fail(state, reason) if state is not None else []

    async def _load(self, session_id: UUID, generation: int) -> LiveRiskState | None:
        state = await self._repo.get(session_id)
        if state is None:
            raise CodeRiskError("리스크 원장이 없습니다")
        if state.generation != generation:
            return None
        # ORM instance_state는 복사하지 않는다. CAS 밖 autoflush도 방지한다.
        return LiveRiskState(**state.model_dump())

    def _plan(self, state: LiveRiskState) -> RiskPlan:
        plan = create_plan(
            entry_price=state.entry_vwap or ZERO,
            qty=state.cumulative_quantity,
            direction=cast(Direction, state.direction),
            generation=state.generation,
            previous_bars=[
                {key: Decimal(value) for key, value in bar.items()} for bar in state.reference_bars
            ],
        )
        if state.fixed_r is None:
            return plan
        sign = Decimal(1) if state.direction == "long" else Decimal(-1)
        return replace(
            plan,
            risk=state.fixed_r,
            stop_loss=plan.entry_price - sign * state.fixed_r,
            tp_price=plan.entry_price + sign * state.fixed_r * POLICY.partial_target_r,
            trailing_activation=plan.entry_price
            + sign * state.fixed_r * POLICY.trailing_activation_r,
            trailing_distance=state.fixed_r * POLICY.trailing_distance_r,
        )

    def _desire_protection(self, state: LiveRiskState, *, stop: Decimal | None = None) -> None:
        desired: dict[str, object] = {
            "token": f"{state.generation}:{state.revision + 1}",
            "quantity": str(state.position_quantity),
            "stop_loss": str(state.provisional_stop),
            "trailing_active": state.trailing_active,
        }
        if state.fixed_r is not None:
            plan = self._plan(state)
            desired.update(
                stop_loss=str(
                    stop
                    if stop is not None
                    else state.protection_desired.get("stop_loss", plan.stop_loss)
                ),
                tp_price=str(plan.tp_price),
                tp_quantity=str(
                    min(
                        state.position_quantity,
                        max(
                            ZERO,
                            state.cumulative_quantity * POLICY.partial_fraction
                            - state.tp_filled_quantity,
                        ),
                    )
                ),
                trailing_activation=str(plan.trailing_activation),
                trailing_distance=str(plan.trailing_distance),
            )
            # 첫 최종 계획만 임시 SL을 확정 VWAP 기준 SL로 교체한다.
            if "tp_price" not in state.protection_desired:
                desired["stop_loss"] = str(plan.stop_loss)
        state.protection_desired = desired
        state.cancels_confirmed = False

    async def _save(self, state: LiveRiskState, *, commit: bool = True) -> list[RiskCommand]:
        if not await self._repo.compare_and_swap(state, state.revision):
            raise CodeRiskError("리스크 원장 CAS 충돌: 재조회가 필요합니다")
        state.revision += 1
        commands = self._commands(state)
        await self._enqueue(state, commands)
        if commit:
            await self._repo.commit()
        return commands

    async def _enqueue(self, state: LiveRiskState, commands: list[RiskCommand]) -> None:
        await self._repo.enqueue_commands(
            [
                CodeRiskCommand(
                    key=command.key,
                    session_id=state.session_id,
                    generation=state.generation,
                    kind=command.kind,
                    payload=command.payload,
                )
                for command in commands
            ]
        )

    async def _fail(
        self, state: LiveRiskState, reason: str, *, commit: bool = True
    ) -> list[RiskCommand]:
        state.new_entries_blocked = True
        state.failure_reason = reason
        state.close_requested = True
        state.pending_reversal = None
        return await self._save(state, commit=commit)

    @staticmethod
    def _commands(state: LiveRiskState) -> list[RiskCommand]:
        prefix = f"risk:{state.session_id}:{state.generation}"
        commands: list[RiskCommand] = []
        if state.new_entries_blocked:
            commands.append(
                RiskCommand("halt_new_entries", prefix + ":halt", {"reason": state.failure_reason})
            )
        if state.close_requested and not state.entry_terminal:
            commands.append(
                RiskCommand(
                    "cancel_entry",
                    prefix + ":cancel_entry",
                    {"order_id": str(state.entry_order_id)},
                )
            )
        if state.close_requested and (state.position_quantity > 0 or not state.entry_terminal):
            commands.append(
                RiskCommand(
                    "flatten",
                    f"{prefix}:flatten:{state.cumulative_quantity}:{state.position_quantity}:{len(state.exit_fills)}",
                    {
                        "quantity": str(
                            max(state.position_quantity, state.expected_quantity)
                            if not state.entry_terminal
                            else state.position_quantity
                        ),
                        "reduce_only": True,
                    },
                )
            )
        elif state.position_quantity > 0 and state.protection_desired != state.protection_applied:
            commands.append(
                RiskCommand(
                    "apply_protection",
                    f"{prefix}:protect:{state.protection_desired['token']}",
                    dict(state.protection_desired),
                )
            )
        elif state.position_quantity == 0 and state.entry_terminal:
            if not state.cancels_confirmed:
                commands.append(RiskCommand("cancel_children", prefix + ":cancel_children", {}))
            elif state.pending_reversal is not None and not state.new_entries_blocked:
                commands.append(
                    RiskCommand(
                        "ready_reversal", prefix + ":reverse", {"direction": state.pending_reversal}
                    )
                )
        elif (
            state.cumulative_quantity == 0
            and not state.entry_terminal
            and not state.close_requested
        ):
            commands.append(
                RiskCommand(
                    "submit_entry",
                    prefix + ":entry",
                    {
                        "order_id": str(state.entry_order_id),
                        "stop_loss": str(state.provisional_stop),
                    },
                )
            )
        return commands

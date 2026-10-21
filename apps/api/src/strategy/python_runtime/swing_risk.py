"""동일 주기 두 봉의 스윙 가격에 고정 R 청산을 적용하는 순수 상태기계."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import pairwise
from typing import Literal

Direction = Literal["long", "short"]
ExitKind = Literal["partial_tp", "stop_loss", "trailing_stop", "close"]


@dataclass(frozen=True)
class RiskPolicy:
    version: str = "swing_two_bar_v1"
    stop_buffer: Decimal = Decimal("0.10")
    partial_target_r: Decimal = Decimal("1.5")
    partial_fraction: Decimal = Decimal("0.5")
    trailing_activation_r: Decimal = Decimal("2")
    trailing_distance_r: Decimal = Decimal("2")


POLICY = RiskPolicy()


@dataclass(frozen=True)
class RiskPlan:
    generation: int
    direction: Direction
    entry_price: Decimal
    initial_qty: Decimal
    reference_extreme: Decimal
    stop_loss: Decimal
    risk: Decimal
    tp_price: Decimal
    trailing_activation: Decimal
    trailing_distance: Decimal
    policy_version: str = POLICY.version


@dataclass(frozen=True)
class RiskState:
    plan: RiskPlan
    remaining_qty: Decimal
    stop_price: Decimal
    tp_filled: bool = False
    trailing_active: bool = False
    pending_close: bool = False


@dataclass(frozen=True)
class RiskEvent:
    generation: int
    kind: ExitKind
    price: Decimal
    qty: Decimal


@dataclass(frozen=True)
class CandleOutcome:
    state: RiskState
    events: tuple[RiskEvent, ...]
    ambiguous: bool
    path: str


class StaleRiskGeneration(ValueError):
    """교체 전 계획의 예약·체결 이벤트를 새 포지션에 적용할 수 없다."""


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"{name} 는 유한한 양수 Decimal 이어야 합니다")


def create_plan(
    *,
    entry_price: Decimal,
    qty: Decimal,
    direction: Direction,
    previous_bars: Sequence[Mapping[str, Decimal]],
    generation: int,
) -> RiskPlan:
    """호출자가 선택한 직전 완료 두 봉만 참조한다. 미래 봉은 받지 않는다."""
    _positive(entry_price, "진입가")
    _positive(qty, "수량")
    if direction not in ("long", "short") or generation < 1:
        raise ValueError("방향 또는 계획 generation 이 올바르지 않습니다")
    if len(previous_bars) != 2:
        raise ValueError("직전 완료 봉은 정확히 두 개여야 합니다")
    for bar in previous_bars:
        _positive(bar["low"], "저가")
        _positive(bar["high"], "고가")
        if bar["low"] > bar["high"]:
            raise ValueError("참조 봉의 저가가 고가보다 높습니다")
    sign = Decimal(1) if direction == "long" else Decimal(-1)
    extreme = (
        min(bar["low"] for bar in previous_bars)
        if direction == "long"
        else max(bar["high"] for bar in previous_bars)
    )
    distance = sign * (entry_price - extreme)
    if distance <= 0:
        raise ValueError("스윙 가격은 진입가의 손실 방향에 있어야 합니다")
    risk = distance * (Decimal(1) + POLICY.stop_buffer)
    stop = entry_price - sign * risk
    target = entry_price + sign * risk * POLICY.partial_target_r
    activation = entry_price + sign * risk * POLICY.trailing_activation_r
    for name, price in (("SL", stop), ("반익절", target), ("트레일링 활성가", activation)):
        _positive(price, name)
    return RiskPlan(
        generation=generation,
        direction=direction,
        entry_price=entry_price,
        initial_qty=qty,
        reference_extreme=extreme,
        stop_loss=stop,
        risk=risk,
        tp_price=target,
        trailing_activation=activation,
        trailing_distance=risk * POLICY.trailing_distance_r,
    )


def initial_state(plan: RiskPlan) -> RiskState:
    return RiskState(plan=plan, remaining_qty=plan.initial_qty, stop_price=plan.stop_loss)


def replace_plan(state: RiskState, new_plan: RiskPlan) -> RiskState:
    """명시적 새 계획만 교체한다. 이미 체결된 수량은 복원하지 않는다."""
    if new_plan.generation <= state.plan.generation:
        raise StaleRiskGeneration("새 계획의 generation 은 현재보다 커야 합니다")
    if state.remaining_qty <= 0:
        raise ValueError("청산된 포지션의 계획은 교체할 수 없습니다")
    if new_plan.direction != state.plan.direction or new_plan.entry_price != state.plan.entry_price:
        raise ValueError("계획 교체는 같은 포지션의 방향과 진입가를 유지해야 합니다")
    # TP/SL/트레일링과 미체결 close 는 새 세대로 바뀌며 잔량만 이어받는다.
    return initial_state(replace(new_plan, initial_qty=state.remaining_qty))


def _check_generation(state: RiskState, generation: int) -> None:
    if generation != state.plan.generation:
        raise StaleRiskGeneration("교체된 계획의 이벤트는 적용할 수 없습니다")


def queue_close(state: RiskState, *, generation: int) -> RiskState:
    _check_generation(state, generation)
    return replace(state, pending_close=state.remaining_qty > 0)


def apply_event(state: RiskState, event: RiskEvent) -> RiskState:
    """세대와 수량을 확인한 체결만 잔량에 반영한다. 입력 상태는 바꾸지 않는다."""
    _check_generation(state, event.generation)
    _positive(event.price, "체결가")
    _positive(event.qty, "체결 수량")
    if event.qty > state.remaining_qty:
        raise ValueError("체결 수량이 포지션 잔량을 초과합니다")
    if event.kind == "partial_tp":
        if state.tp_filled or event.qty != state.plan.initial_qty * POLICY.partial_fraction:
            raise ValueError("반익절은 계획 수량의 절반을 한 번만 체결할 수 있습니다")
        return replace(state, remaining_qty=state.remaining_qty - event.qty, tp_filled=True)
    if event.kind not in ("stop_loss", "trailing_stop", "close"):
        raise ValueError("지원하지 않는 청산 이벤트입니다")
    if event.qty != state.remaining_qty:
        raise ValueError("최종 청산 이벤트는 현재 잔량 전체를 청산해야 합니다")
    return replace(state, remaining_qty=Decimal(0), pending_close=False)


def _fill(state: RiskState, kind: ExitKind, price: Decimal) -> tuple[RiskState, RiskEvent]:
    qty = (
        state.plan.initial_qty * POLICY.partial_fraction
        if kind == "partial_tp"
        else state.remaining_qty
    )
    event = RiskEvent(state.plan.generation, kind, price, qty)
    return apply_event(state, event), event


def _stop_hit(state: RiskState, price: Decimal) -> bool:
    return (
        price <= state.stop_price if state.plan.direction == "long" else price >= state.stop_price
    )


def _favorable(state: RiskState, price: Decimal) -> tuple[RiskState, tuple[RiskEvent, ...]]:
    sign = Decimal(1) if state.plan.direction == "long" else Decimal(-1)
    events: tuple[RiskEvent, ...] = ()
    if not state.tp_filled and sign * (price - state.plan.tp_price) >= 0:
        state, event = _fill(state, "partial_tp", state.plan.tp_price)
        events = (event,)
    if sign * (price - state.plan.trailing_activation) >= 0:
        state = replace(state, trailing_active=True)
    if state.trailing_active:
        proposed = price - sign * state.plan.trailing_distance
        # 2R 활성 순간 본절, 이후 유리한 방향으로만 이동한다.
        stop = (
            max(state.stop_price, state.plan.entry_price, proposed)
            if sign > 0
            else min(state.stop_price, state.plan.entry_price, proposed)
        )
        state = replace(state, stop_price=stop)
    return state, events


def _replay_path(state: RiskState, prices: tuple[Decimal, ...], path: str) -> CandleOutcome:
    events: list[RiskEvent] = []
    if state.remaining_qty == 0:
        return CandleOutcome(state, (), False, path)
    if state.pending_close or _stop_hit(state, prices[0]):
        kind: ExitKind = (
            "close"
            if state.pending_close
            else "trailing_stop"
            if state.trailing_active
            else "stop_loss"
        )
        state, event = _fill(state, kind, prices[0])
        return CandleOutcome(state, (event,), False, path)
    state, opening_events = _favorable(state, prices[0])
    # 기존 브로커와 같이 대기 중인 TP 지정가의 유리한 시가 갭은 시가로 체결한다.
    opening_events = tuple(replace(event, price=prices[0]) for event in opening_events)
    events.extend(opening_events)
    sign = Decimal(1) if state.plan.direction == "long" else Decimal(-1)
    for start, end in pairwise(prices):
        if state.remaining_qty == 0:
            break
        if sign * (end - start) >= 0:
            state, favorable_events = _favorable(state, end)
            events.extend(favorable_events)
        elif _stop_hit(state, end):
            # 이 세그먼트에 도달한 시점의 SL 만 사용한다. 이전 open 으로 소급하지 않는다.
            kind = "trailing_stop" if state.trailing_active else "stop_loss"
            state, event = _fill(state, kind, state.stop_price)
            events.append(event)
    return CandleOutcome(state, tuple(events), False, path)


def _marked_pnl(outcome: CandleOutcome, close: Decimal) -> Decimal:
    plan = outcome.state.plan
    sign = Decimal(1) if plan.direction == "long" else Decimal(-1)
    realized = sum(
        (sign * (event.price - plan.entry_price) * event.qty for event in outcome.events),
        Decimal(0),
    )
    return realized + sign * (close - plan.entry_price) * outcome.state.remaining_qty


def replay_candle(
    state: RiskState,
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
) -> CandleOutcome:
    """두 OHLC 경로 중 수수료·슬리피지 전 종가 평가손익이 낮은 경로를 채택한다.

    실제 틱 순서의 증명이나 모든 가능한 경로의 최악값은 아니다. 결과가 다른 분봉은
    ambiguous 로 남긴다. 동률이면 비활성·덜 보호적인 SL 을 우선하고 경로 순서로 고정한다.
    """
    for name, value in (("시가", open_), ("고가", high), ("저가", low), ("종가", close)):
        _positive(value, name)
    if not low <= min(open_, close) <= max(open_, close) <= high:
        raise ValueError("OHLC 가격 관계가 올바르지 않습니다")
    if state.remaining_qty > 0 and not state.pending_close:
        long = state.plan.direction == "long"
        stop_untouched = low > state.stop_price if long else high < state.stop_price
        if stop_untouched:
            if not state.trailing_active:
                threshold = (
                    state.plan.trailing_activation if state.tp_filled else state.plan.tp_price
                )
                target_untouched = high < threshold if long else low > threshold
                if target_untouched:
                    return CandleOutcome(state, (), False, "O-H-L-C")
            elif state.tp_filled:
                # 최대로 당긴 SL 조차 분봉 밖이면 두 경로 모두 체결 없이 같은 SL 이 된다.
                proposed = (
                    max(
                        state.stop_price,
                        state.plan.entry_price,
                        high - state.plan.trailing_distance,
                    )
                    if long
                    else min(
                        state.stop_price, state.plan.entry_price, low + state.plan.trailing_distance
                    )
                )
                untouched = proposed < low if long else proposed > high
                if untouched:
                    return CandleOutcome(replace(state, stop_price=proposed), (), False, "O-H-L-C")
    high_first = _replay_path(state, (open_, high, low, close), "O-H-L-C")
    low_first = _replay_path(state, (open_, low, high, close), "O-L-H-C")
    sign = Decimal(1) if state.plan.direction == "long" else Decimal(-1)

    def rank(outcome: CandleOutcome) -> tuple[Decimal, bool, Decimal]:
        return (
            _marked_pnl(outcome, close),
            outcome.state.trailing_active,
            sign * outcome.state.stop_price,
        )

    selected = min((high_first, low_first), key=rank)
    ambiguous = high_first.state != low_first.state or high_first.events != low_first.events
    return replace(selected, ambiguous=ambiguous)

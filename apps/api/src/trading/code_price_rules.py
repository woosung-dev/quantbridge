"""이론 R을 보존하면서 demo 거래소 눈금의 실제 주문·보호 가격을 계산한다."""

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Literal


def tick_price(value: Decimal, tick: Decimal, *, up: bool) -> Decimal:
    if any(not number.is_finite() or number <= 0 for number in (value, tick)):
        raise ValueError("가격·tick은 유한한 양수여야 합니다")
    result = (value / tick).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR) * tick
    if result <= 0:
        raise ValueError("눈금 정규화 후 가격이 양수가 아닙니다")
    return result


def protection_prices(
    *,
    direction: Literal["long", "short"],
    entry_price: Decimal,
    stop_loss: Decimal,
    tick: Decimal,
    distance: Decimal | None,
    activation: Decimal | None,
    breakeven_required: bool,
) -> dict[str, object]:
    long = direction == "long"
    breakeven = tick_price(entry_price, tick, up=long)
    stop = tick_price(stop_loss, tick, up=not long)
    if breakeven_required:
        stop = max(stop, breakeven) if long else min(stop, breakeven)
    result: dict[str, object] = {
        "tick": str(tick),
        "entry_price_reference": str(entry_price),
        "stop_loss": str(stop),
        "breakeven_price": str(breakeven),
        "breakeven_required": breakeven_required,
    }
    if (distance is None) != (activation is None):
        raise ValueError("native 거리와 활성가가 함께 필요합니다")
    if distance is not None and activation is not None:
        actual_distance = tick_price(distance, tick, up=True)
        candidate = tick_price(activation, tick, up=long)
        actual_activation = (
            max(candidate, breakeven + actual_distance)
            if long
            else min(candidate, breakeven - actual_distance)
        )
        if actual_activation <= 0:
            raise ValueError("native 활성가가 양수가 아닙니다")
        initial_stop = (
            actual_activation - actual_distance if long else actual_activation + actual_distance
        )
        if (long and initial_stop < entry_price) or (not long and initial_stop > entry_price):
            raise ValueError("native 활성 시 손익분기 조건이 성립하지 않습니다")
        result.update(
            trailing_distance=str(actual_distance),
            active_price=str(actual_activation),
            native_initial_stop=str(initial_stop),
            activation_delay=str(abs(actual_activation - activation)),
            native_be_parameter_verified=True,
        )
    return result

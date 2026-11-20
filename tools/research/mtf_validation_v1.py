"""전략 재실행 없이 체결 원장으로 callback 시점의 단일 포지션을 복원한다."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Context, Decimal, localcontext


def callback_positions(bars: list[dict], fills: list[dict], timeframe: str, decimal_context: dict) -> list[dict]:
    """다음 부모 시가의 fill을 이전 부모 종가 callback에 미리 포함하지 않는다."""
    minutes = {"1h": 60, "4h": 240, "1d": 1440}[timeframe]
    if not bars:
        raise ValueError("부모 봉이 없습니다")
    moments = [datetime.fromisoformat(fill["timestamp"]) for fill in fills]
    if any(t.tzinfo is None for t in moments) or any(a > b for a, b in zip(moments, moments[1:])):
        raise ValueError("체결 시각의 시간대·순서 오류")
    cursor, remaining, direction, average, generation = 0, Decimal(0), "flat", None, None
    positions = []
    previous_end = None
    with localcontext(Context(**decimal_context)):
        for bar in bars:
            start = datetime.fromisoformat(bar["timestamp"])
            end = start + timedelta(minutes=minutes)
            if start.tzinfo is None or (previous_end is not None and start < previous_end):
                raise ValueError("부모 시각의 시간대·순서 오류")
            while cursor < len(fills) and moments[cursor] < end:
                fill = fills[cursor]
                quantity = Decimal(fill["quantity"])
                if not quantity.is_finite() or quantity <= 0:
                    raise ValueError("체결 수량 오류")
                if fill["kind"] == "entry":
                    if remaining != 0 or fill["direction"] not in {"long", "short"}:
                        raise ValueError("열린 포지션과 겹치는 신규 진입")
                    remaining, direction = quantity, fill["direction"]
                    price = Decimal(fill["price"])
                    if not price.is_finite() or price <= 0:
                        raise ValueError("진입 가격 오류")
                    average, generation = str(price), fill["generation"]
                else:
                    if generation != fill["generation"] or quantity > remaining:
                        raise ValueError("청산 세대·잔량 오류")
                    remaining -= quantity
                    if remaining == 0:
                        direction, average, generation = "flat", None, None
                cursor += 1
            positions.append({"size": str(remaining) if remaining != 0 else "0", "direction": direction,
                              "average_price": average})
            previous_end = end
    if cursor != len(fills):
        raise ValueError("마지막 callback 이후의 미래 체결")
    return positions

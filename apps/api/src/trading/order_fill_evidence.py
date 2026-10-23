"""주문 상태와 실제 체결 증거를 분리한다. legacy 실패 주문의 추정 손익은 제외한다."""

from decimal import Decimal


def has_recorded_order_fill(order: object) -> bool:
    state = getattr(order, "state", None)
    if state == "filled":
        return True
    quantity = getattr(order, "filled_quantity", None)
    return (
        state in {"cancelled", "rejected"}
        and getattr(order, "risk_context", None) is not None
        and isinstance(quantity, Decimal)
        and quantity.is_finite()
        and quantity > 0
    )

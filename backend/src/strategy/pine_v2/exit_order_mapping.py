# ExitOrderKind 를 라이브 주문 프리미티브(OrderSubmit 필드)로 매핑하는 순수함수.
"""Wave 1 — exit_orders.ExitOrderKind 계약의 첫 라이브 소비자.

백테스트 sim(exit_orders) 과 라이브 주문이 동일 enum + 체결 가정을 공유하도록,
ExitOrderKind 를 라이브 OrderSubmit 프리미티브로 매핑한다 (백테스트↔라이브 정합).

설계 (★ exit_orders 계약):
- TAKE_PROFIT  → reduce-only **limit**  (resting limit = maker). limit_price=청산가.
- STOP_LOSS    → reduce-only **trigger market** (trigger 시장체결 = taker). trigger_price=청산가.
- TRAILING_STOP→ reduce-only **trigger market** (ratchet trigger 시장체결 = taker). trigger_price=청산가.

fill_type 은 백테스트 cost SSOT(`exit_orders.fill_type_for`)와 1:1 정합을 불변식으로 고정한다.
ExitOrderKind 는 import 재사용(중복 정의 금지). 이 모듈은 매핑만 — 실제 주문 placement
(triggerDirection 결정, OCO 그룹핑)은 Wave 2 책임.

OrderSubmit 변환 (Wave 2 placement 가 소비):
- TP:        OrderSubmit(type=order_type, price=limit_price, reduce_only=True)
- SL/Trail:  OrderSubmit(type=order_type, trigger_price=trigger_price, reduce_only=True)
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from src.strategy.pine_v2.exit_orders import ExitOrderKind, fill_type_for
from src.trading.models import OrderType


@dataclass(frozen=True, slots=True)
class ExitOrderPrimitive:
    """ExitOrderKind 의 라이브 주문 프리미티브 표현 (OrderSubmit 빌드 입력).

    exit 주문은 전부 reduce-only (포지션 청산 전용 → over-fill 방지).
    """

    kind: ExitOrderKind
    order_type: OrderType
    reduce_only: bool
    # TP(resting limit) 의 지정가. SL/Trail 은 None.
    limit_price: Decimal | None
    # SL/Trail(trigger market) 의 트리거가. TP 는 None.
    trigger_price: Decimal | None
    # 백테스트 cost SSOT 와 정합되는 체결 타입 (maker=resting limit, taker=trigger 시장체결).
    fill_type: Literal["maker", "taker"]


def map_exit_kind(kind: ExitOrderKind, *, exit_price: Decimal) -> ExitOrderPrimitive:
    """ExitOrderKind → ExitOrderPrimitive 순수 매핑.

    exit_price = 청산 트리거가(SL/Trail) 또는 지정가(TP). fill_type 은 항상
    `fill_type_for(kind)` 와 일치하도록 도출한다.
    """
    fill_type = fill_type_for(kind)
    if kind == ExitOrderKind.TAKE_PROFIT:
        # resting limit → maker. 지정가 = exit_price, trigger 없음.
        return ExitOrderPrimitive(
            kind=kind,
            order_type=OrderType.limit,
            reduce_only=True,
            limit_price=exit_price,
            trigger_price=None,
            fill_type=fill_type,
        )
    # STOP_LOSS / TRAILING_STOP — trigger market → taker. 트리거가 = exit_price.
    return ExitOrderPrimitive(
        kind=kind,
        order_type=OrderType.market,
        reduce_only=True,
        limit_price=None,
        trigger_price=exit_price,
        fill_type=fill_type,
    )

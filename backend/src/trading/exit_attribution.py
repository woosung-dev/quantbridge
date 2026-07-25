# 거래소 청산 행의 출처 분류와 전략 귀속을 순수하게 판정한다.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.trading.models import ExitAttribution, ExitClassification
from src.trading.providers import ClosedOrderMeta

_TAKE_PROFIT_CREATE_TYPES = frozenset({"createbytakeprofit", "createbypartialtakeprofit"})
_STOP_LOSS_CREATE_TYPES = frozenset({"createbystoploss", "createbypartialstoploss"})
_TRAILING_CREATE_TYPES = frozenset({"createbytrailingstop"})


@dataclass(frozen=True, slots=True)
class OrderFact:
    """귀속 추정에 필요한 우리 주문의 최소 사실이다. 리포지토리 모델을 이 모듈에 들이지 않는다."""

    order_id: UUID
    strategy_id: UUID
    symbol: str
    side_is_buy: bool
    reduce_only: bool
    quantity: Decimal
    filled_price: Decimal | None
    filled_at: datetime


def classify_exit(
    *, matched_order_id: UUID | None, meta: ClosedOrderMeta | None
) -> ExitClassification:
    """주문 매칭과 거래소 메타로 청산 출처를 보수적으로 분류한다."""
    if matched_order_id is not None:
        return ExitClassification.ours
    if meta is None:
        return ExitClassification.unknown
    # 우리 앱은 orderLinkId 에 Order.id(UUID4) 를 그대로 싣는다. 값이 있다는 것만으로
    # ours 로 보면 외부 도구가 임의 client order id 를 단 주문까지 우리 것으로 오분류되고,
    # 그러면 미귀속 알림에서 조용히 빠진다.
    if meta.order_link_id and _is_our_client_order_id(meta.order_link_id):
        return ExitClassification.ours

    create_type = (meta.create_type or "").casefold()
    if create_type in _TAKE_PROFIT_CREATE_TYPES:
        return ExitClassification.bracket_tp
    if create_type in _STOP_LOSS_CREATE_TYPES:
        return ExitClassification.bracket_sl
    if create_type in _TRAILING_CREATE_TYPES:
        return ExitClassification.trailing
    if "liquidation" in create_type or "adl" in create_type:
        return ExitClassification.liquidation

    # createType 이 비거나 낯설어도 stopOrderType 이 조건부 유래를 밝힌다. close-completeness
    # 스프린트가 이미 이 필드를 엄격 분류자로 세웠다.
    stop_order_type = (meta.stop_order_type or "").casefold()
    if "takeprofit" in stop_order_type:
        return ExitClassification.bracket_tp
    if "stoploss" in stop_order_type:
        return ExitClassification.bracket_sl
    if "trailing" in stop_order_type:
        return ExitClassification.trailing

    if create_type == "createbyuser":
        return ExitClassification.external_manual
    return ExitClassification.unknown


def _is_our_client_order_id(order_link_id: str) -> bool:
    """orderLinkId 가 우리가 싣는 Order.id(UUID) 형식인지 본다."""
    try:
        UUID(order_link_id)
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def attribute_exit(
    *,
    symbol: str,
    avg_entry_price: Decimal | None,
    exit_at: datetime,
    our_filled_orders: Sequence[OrderFact],
) -> tuple[ExitAttribution, UUID | None]:
    """확정 매칭이 없는 청산의 보수적 전략 귀속을 판정한다."""
    # 실측 표본 4건에서는 4/4 정답이었지만 활성 세션이 사실상 하나였다. 같은 계정·심볼에
    # 서로 다른 전략의 활성 세션이 공존할 수 있으므로 검정력이 없다. inferred는 이번
    # 스프린트에서 리스크 게이트 입력으로 절대 쓰지 않는다.
    if avg_entry_price is None:
        return ExitAttribution.none, None

    relevant_orders = sorted(
        (
            order
            for order in our_filled_orders
            if order.symbol == symbol and order.filled_at <= exit_at
        ),
        key=lambda order: order.filled_at,
    )
    entry_candidates = [
        order
        for order in relevant_orders
        if not order.reduce_only and order.filled_price == avg_entry_price
    ]
    if len(entry_candidates) != 1:
        return ExitAttribution.none, None

    position = sum(
        (order.quantity if order.side_is_buy else -order.quantity for order in relevant_orders),
        Decimal("0"),
    )
    if position == Decimal("0"):
        return ExitAttribution.none, None
    return ExitAttribution.inferred, entry_candidates[0].strategy_id

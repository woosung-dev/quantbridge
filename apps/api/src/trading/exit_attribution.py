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
# ★[BL-728] — 종전 판정은 `"liquidation" in create_type` 이었는데 **Bybit 실제 enum 은
#   `CreateByLiq`** 다. casefold 하면 `createbyliq` 라 그 부분문자열이 안 걸려 강제청산이
#   `unknown` 으로 샜다. 마진율 강제감축(`CreateByMmRateClose`)도 같은 성질이라 함께 넣는다.
_LIQUIDATION_CREATE_TYPES = frozenset({"createbyliq", "createbymmrateclose"})


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
    *,
    matched_order_id: UUID | None,
    meta: ClosedOrderMeta | None,
    known_order_ids: frozenset[UUID],
) -> ExitClassification:
    """주문 매칭과 거래소 메타로 청산 출처를 보수적으로 분류한다.

    `known_order_ids` = 이 청산이 속한 **계정**의 실재하는 `Order.id` 집합. 기본값을
    주지 않는 이유는, 빈 기본값이 fail-closed 이긴 하지만 미래의 호출자가 인자를
    빼먹고도 조용히 통과해 `ours` 라벨을 영구히 잃게 만들기 때문이다(BL-457).
    """
    if matched_order_id is not None:
        return ExitClassification.ours
    if meta is None:
        return ExitClassification.unknown
    # 우리 앱은 orderLinkId 에 Order.id(UUID4) 를 그대로 싣는다. 그러나 UUID 로
    # 파싱된다는 것은 **필요조건일 뿐**이다 — 외부 도구도 UUID 모양 client order id 를
    # 달 수 있고, 그러면 그 청산이 운영자 미귀속 알림에서 조용히 빠진다(BL-457).
    # 실재 확인(계정 스코프 membership)이 충분조건이다.
    link_id = parse_our_order_link_id(meta.order_link_id)
    if link_id is not None and link_id in known_order_ids:
        return ExitClassification.ours

    create_type = (meta.create_type or "").casefold()
    if create_type in _TAKE_PROFIT_CREATE_TYPES:
        return ExitClassification.bracket_tp
    if create_type in _STOP_LOSS_CREATE_TYPES:
        return ExitClassification.bracket_sl
    if create_type in _TRAILING_CREATE_TYPES:
        return ExitClassification.trailing
    if create_type in _LIQUIDATION_CREATE_TYPES:
        return ExitClassification.liquidation
    # ★ADL 만 부분문자열로 남긴다 — 실제 값이 `CreateByAdl_PassThrough` 라 접미사가 붙어
    #   집합 동등으로는 안 걸린다. 위 3종·강제청산과 달리 여기만 접미사 변종이 실재한다.
    if "adl" in create_type:
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

    # UUID 형식이지만 실재 확인이 안 된 행은 여기서 멈춘다. `external_manual` 은
    # "사람이 거래소 UI 에서 Close 를 눌렀다" 는 단정이고, 사람은 UUID4 를 타이핑하지
    # 않는다. 그 라벨은 운영자가 알림 본문에서 읽는 문자열이라 유령 수동거래를 찾아
    # 헤매게 만든다. 모른다고 말하는 것이 정직하다.
    if link_id is not None:
        return ExitClassification.unknown
    if create_type == "createbyuser":
        return ExitClassification.external_manual
    return ExitClassification.unknown


def parse_our_order_link_id(order_link_id: str | None) -> UUID | None:
    """orderLinkId 가 우리가 싣는 Order.id(UUID) 형식이면 그 UUID 를 돌려준다.

    공개인 이유 — 스윕이 실재 확인용 IN-list 후보를 만들 때 **같은 정의**를 써야 한다.
    형식 판정이 두 곳에 복제되면 한쪽만 고쳐지는 날 라벨이 조용히 갈린다.
    """
    if not order_link_id:
        return None
    try:
        return UUID(order_link_id)
    except (AttributeError, TypeError, ValueError):
        return None


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

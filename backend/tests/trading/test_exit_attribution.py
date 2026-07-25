# 거래소 청산 출처 분류와 전략 귀속의 순수 계약을 검증한다.

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.trading.exit_attribution import OrderFact, attribute_exit, classify_exit
from src.trading.models import ExitAttribution, ExitClassification
from src.trading.providers import ClosedOrderMeta


def _fact(
    *,
    price: str = "100",
    side_is_buy: bool = True,
    reduce_only: bool = False,
    filled_at: datetime | None = None,
) -> OrderFact:
    return OrderFact(
        order_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        side_is_buy=side_is_buy,
        reduce_only=reduce_only,
        quantity=Decimal("1"),
        filled_price=Decimal(price),
        filled_at=filled_at or datetime(2026, 7, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("create_type", "expected"),
    [
        ("CreateByTakeProfit", ExitClassification.bracket_tp),
        ("createbypartialtakeprofit", ExitClassification.bracket_tp),
        ("CreateByStopLoss", ExitClassification.bracket_sl),
        ("CreateByTrailingStop", ExitClassification.trailing),
        ("CreateByLiquidation", ExitClassification.liquidation),
        ("CreateByAdl", ExitClassification.liquidation),
        ("CreateByUser", ExitClassification.external_manual),
    ],
)
def test_classify_exit_known_create_types_case_insensitively(
    create_type: str, expected: ExitClassification
) -> None:
    assert classify_exit(
        matched_order_id=None,
        meta=ClosedOrderMeta("exchange", create_type, None, None),
    ) == expected


def test_classify_exit_prioritizes_matched_order_and_order_link_id() -> None:
    assert classify_exit(matched_order_id=uuid4(), meta=None) == ExitClassification.ours
    # 우리 앱은 orderLinkId 에 Order.id(UUID4) 를 그대로 싣는다.
    assert classify_exit(
        matched_order_id=None,
        meta=ClosedOrderMeta("exchange", "CreateByUser", None, str(uuid4())),
    ) == ExitClassification.ours


def test_classify_exit_unknown_fallbacks() -> None:
    assert classify_exit(matched_order_id=None, meta=None) == ExitClassification.unknown
    assert classify_exit(
        matched_order_id=None,
        meta=ClosedOrderMeta("exchange", "CreateBySystem", None, None),
    ) == ExitClassification.unknown


def test_attribute_exit_requires_matching_entry_price_and_open_position() -> None:
    exit_at = datetime(2026, 7, 2, tzinfo=UTC)
    entry = _fact()
    closing_sell = _fact(side_is_buy=False, reduce_only=True, filled_at=exit_at - timedelta(hours=1))

    assert attribute_exit(
        symbol="BTC/USDT",
        avg_entry_price=Decimal("100"),
        exit_at=exit_at,
        our_filled_orders=[entry, closing_sell],
    ) == (ExitAttribution.none, None)
    assert attribute_exit(
        symbol="BTC/USDT",
        avg_entry_price=Decimal("101"),
        exit_at=exit_at,
        our_filled_orders=[entry],
    ) == (ExitAttribution.none, None)


def test_attribute_exit_infers_only_one_matching_entry() -> None:
    exit_at = datetime(2026, 7, 2, tzinfo=UTC)
    entry = _fact()

    assert attribute_exit(
        symbol="BTC/USDT",
        avg_entry_price=Decimal("100"),
        exit_at=exit_at,
        our_filled_orders=[entry],
    ) == (ExitAttribution.inferred, entry.strategy_id)
    assert attribute_exit(
        symbol="BTC/USDT",
        avg_entry_price=Decimal("100"),
        exit_at=exit_at,
        our_filled_orders=[entry, _fact()],
    ) == (ExitAttribution.none, None)


def test_attribute_exit_reproduces_observed_orphans_conservatively() -> None:
    exit_at = datetime(2026, 7, 2, tzinfo=UTC)
    orders = [_fact(price=price) for price in ("62879.4", "62871.8", "62848.5", "62846.3", "62846.2")]

    outcomes = [
        attribute_exit(
            symbol="BTC/USDT",
            avg_entry_price=Decimal(price),
            exit_at=exit_at,
            our_filled_orders=orders,
        )[0]
        for price in ("62846.2", "62624", "62502.2", "64963.1")
    ]

    assert outcomes == [
        ExitAttribution.inferred,
        ExitAttribution.none,
        ExitAttribution.none,
        ExitAttribution.none,
    ]


def test_classify_falls_back_to_stop_order_type_when_create_type_is_blank() -> None:
    """Bybit 은 createType 이 비고 stopOrderType 만 채워진 조건부 주문을 낸다.

    close-completeness 스프린트가 이미 stopOrderType 을 엄격 분류자로 세웠는데,
    createType 만 보면 그 행이 unknown 으로 떨어져 브래킷 exit 의 첫 발화를 놓친다.
    """
    from src.trading.exit_attribution import classify_exit
    from src.trading.models import ExitClassification
    from src.trading.providers import ClosedOrderMeta

    def _meta(stop: str) -> ClosedOrderMeta:
        return ClosedOrderMeta(
            order_id="o-1", create_type="", stop_order_type=stop, order_link_id=None
        )

    assert classify_exit(matched_order_id=None, meta=_meta("TakeProfit")) is ExitClassification.bracket_tp
    assert classify_exit(matched_order_id=None, meta=_meta("PartialStopLoss")) is ExitClassification.bracket_sl
    assert classify_exit(matched_order_id=None, meta=_meta("TrailingStop")) is ExitClassification.trailing


def test_classify_requires_our_uuid_shape_before_claiming_ownership() -> None:
    """외부 도구가 임의 client order id 를 달면 ours 로 오분류돼 미귀속 알림에서 빠진다."""
    from uuid import uuid4

    from src.trading.exit_attribution import classify_exit
    from src.trading.models import ExitClassification
    from src.trading.providers import ClosedOrderMeta

    ours = ClosedOrderMeta(
        order_id="o-1", create_type="CreateByUser", stop_order_type=None, order_link_id=str(uuid4())
    )
    foreign = ClosedOrderMeta(
        order_id="o-2", create_type="CreateByUser", stop_order_type=None, order_link_id="tv-bot-42"
    )
    assert classify_exit(matched_order_id=None, meta=ours) is ExitClassification.ours
    assert classify_exit(matched_order_id=None, meta=foreign) is ExitClassification.external_manual

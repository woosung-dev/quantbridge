# 거래소 청산 출처 분류와 전략 귀속의 순수 계약을 검증한다.

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

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
        # ★[BL-728] — 여기 있던 `"CreateByLiquidation"` 은 **Bybit 이 내지 않는 값**이었다.
        #   종전 구현이 `"liquidation" in create_type` 이라 그 가짜 값에는 걸렸고, 그래서
        #   이 파라미터가 초록인 채로 진짜 강제청산(`CreateByLiq`)이 `unknown` 으로 샜다.
        #   실제 enum 만 남긴다.
        ("CreateByLiq", ExitClassification.liquidation),
        ("createbyliq", ExitClassification.liquidation),
        ("CreateByMmRateClose", ExitClassification.liquidation),
        # ADL 은 접미사 변종이 실재하므로 부분문자열 축을 유지한다.
        ("CreateByAdl", ExitClassification.liquidation),
        ("CreateByAdl_PassThrough", ExitClassification.liquidation),
        ("CreateByUser", ExitClassification.external_manual),
    ],
)
def test_classify_exit_known_create_types_case_insensitively(
    create_type: str, expected: ExitClassification
) -> None:
    assert (
        classify_exit(
            matched_order_id=None,
            meta=ClosedOrderMeta("exchange", create_type, None, None),
            known_order_ids=frozenset(),
        )
        == expected
    )


def test_classify_exit_no_longer_matches_liquidation_by_substring() -> None:
    """[BL-728] 음성 대조 — 부분문자열 판정이 실제로 없어졌는지 재는 유일한 케이스.

    ★위 파라미터 표만으로는 판별력이 없다. `"liquidation" in create_type` 를 그대로 두고
    `_LIQUIDATION_CREATE_TYPES` 를 **추가**하기만 해도 표는 전건 초록이다. 부분문자열 축이
    죽었다는 것은 「부분문자열로만 걸리던 값이 이제 안 걸린다」로만 증명된다.

    `CreateByLiquidation` 은 Bybit 이 내지 않는 값이다 — 모르는 값이므로 `unknown` 이 정답이다.
    """
    assert (
        classify_exit(
            matched_order_id=None,
            meta=ClosedOrderMeta("exchange", "CreateByLiquidation", None, None),
            known_order_ids=frozenset(),
        )
        == ExitClassification.unknown
    )


def test_classify_exit_requires_membership_for_the_link_id_path() -> None:
    """BL-457 — link-id 경로의 `ours` 는 실재하는 Order 행을 요구한다.

    branch 1(거래소 주문 id 매칭)은 이미 실측 매칭이므로 `known_order_ids` 를 참조하지
    않아야 한다. 빈 집합으로도 `ours` 가 유지되는 것이 그 증명이다.
    """
    assert (
        classify_exit(matched_order_id=uuid4(), meta=None, known_order_ids=frozenset())
        == ExitClassification.ours
    )
    # 우리 앱은 orderLinkId 에 Order.id(UUID4) 를 그대로 싣는다. 그러나 UUID 로
    # 파싱된다는 것은 필요조건일 뿐이고, 실재 확인이 충분조건이다.
    ours_id = uuid4()
    meta = ClosedOrderMeta("exchange", "CreateByUser", None, str(ours_id))
    assert (
        classify_exit(matched_order_id=None, meta=meta, known_order_ids=frozenset({ours_id}))
        == ExitClassification.ours
    )


def test_classify_exit_unknown_fallbacks() -> None:
    assert (
        classify_exit(matched_order_id=None, meta=None, known_order_ids=frozenset())
        == ExitClassification.unknown
    )
    assert (
        classify_exit(
            matched_order_id=None,
            meta=ClosedOrderMeta("exchange", "CreateBySystem", None, None),
            known_order_ids=frozenset(),
        )
        == ExitClassification.unknown
    )


def test_attribute_exit_requires_matching_entry_price_and_open_position() -> None:
    exit_at = datetime(2026, 7, 2, tzinfo=UTC)
    entry = _fact()
    closing_sell = _fact(
        side_is_buy=False, reduce_only=True, filled_at=exit_at - timedelta(hours=1)
    )

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
    orders = [
        _fact(price=price) for price in ("62879.4", "62871.8", "62848.5", "62846.3", "62846.2")
    ]

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

    empty: frozenset[UUID] = frozenset()
    assert (
        classify_exit(matched_order_id=None, meta=_meta("TakeProfit"), known_order_ids=empty)
        is ExitClassification.bracket_tp
    )
    assert (
        classify_exit(matched_order_id=None, meta=_meta("PartialStopLoss"), known_order_ids=empty)
        is ExitClassification.bracket_sl
    )
    assert (
        classify_exit(matched_order_id=None, meta=_meta("TrailingStop"), known_order_ids=empty)
        is ExitClassification.trailing
    )


def test_classify_requires_a_real_order_row_before_claiming_ownership() -> None:
    """BL-457 — 같은 meta 가 `known_order_ids` 하나로 갈린다.

    이전 계약은 `orderLinkId` 가 UUID 로 **파싱되기만** 하면 `ours` 였다. 그래서 UUID
    모양 client order id 를 단 외부 청산이 운영자 알림(`classification != ours` 필터)에서
    조용히 빠졌다. 실측 — 원장 4행 전부 `create_type='CreateByUser'` 이고 `ours` 3행과
    `external_manual` 1행을 가른 유일한 차이가 `order_link_id` UUID 유무였다.
    """
    ours_id = uuid4()
    meta = ClosedOrderMeta(
        order_id="o-1",
        create_type="CreateByUser",
        stop_order_type=None,
        order_link_id=str(ours_id),
    )

    assert (
        classify_exit(matched_order_id=None, meta=meta, known_order_ids=frozenset({ours_id}))
        is ExitClassification.ours
    )
    # 실재하지 않으면 소유를 주장하지 않는다.
    assert (
        classify_exit(matched_order_id=None, meta=meta, known_order_ids=frozenset())
        is not ExitClassification.ours
    )
    # 다른 계정/다른 주문의 UUID 는 우리 것이 아니다 — 형식만으로는 구분되지 않는다.
    assert (
        classify_exit(matched_order_id=None, meta=meta, known_order_ids=frozenset({uuid4()}))
        is not ExitClassification.ours
    )


def test_classify_prefers_bracket_evidence_over_an_unverifiable_link_id() -> None:
    """거래소가 진술한 createType 은 link-id 형태보다 강한 증거다.

    이전 구현은 link-id 분기가 createType 분기보다 앞서서, UUID 모양 id 를 단 행의
    TP/SL/청산 유래를 **버렸다**. 실재 확인을 요구하면 그 증거가 되살아난다.
    """
    meta = ClosedOrderMeta(
        order_id="o-1",
        create_type="CreateByTakeProfit",
        stop_order_type=None,
        order_link_id=str(uuid4()),
    )
    assert (
        classify_exit(matched_order_id=None, meta=meta, known_order_ids=frozenset())
        is ExitClassification.bracket_tp
    )


def test_classify_does_not_call_an_unverifiable_uuid_link_a_manual_close() -> None:
    """사람은 UUID4 를 타이핑하지 않는다.

    미확인 UUID link id + `CreateByUser` 를 `external_manual` 로 부르면 "사람이 거래소
    UI 에서 Close 를 눌렀다" 고 단정하는 셈이다. 그 문자열은 운영자가 알림 본문에서
    읽는 값이라 유령 수동거래를 찾아 헤매게 만든다. 모른다고 말하는 것이 정직하다.
    """
    meta = ClosedOrderMeta(
        order_id="o-1",
        create_type="CreateByUser",
        stop_order_type=None,
        order_link_id=str(uuid4()),
    )
    assert (
        classify_exit(matched_order_id=None, meta=meta, known_order_ids=frozenset())
        is ExitClassification.unknown
    )
    # 형식조차 우리 것이 아니면 거래소 진술을 그대로 받는다.
    foreign = ClosedOrderMeta(
        order_id="o-2", create_type="CreateByUser", stop_order_type=None, order_link_id="tv-bot-42"
    )
    assert (
        classify_exit(matched_order_id=None, meta=foreign, known_order_ids=frozenset())
        is ExitClassification.external_manual
    )


def test_attribute_exit_compares_symbol_strings_exactly() -> None:
    """BL-464 — 이 순수 함수는 정확 문자열 동등만 한다. 공간 정렬은 호출자 책임이다.

    `_fact()` 의 심볼은 우리 canonical(`BTC/USDT`)이고 거래소 원장은 원문(`BTCUSDT`)을
    준다. 호출자가 두 피연산자를 같은 공간으로 내리지 않으면 귀속이 영구히 `none` 이다.
    """
    exit_at = datetime(2026, 7, 2, tzinfo=UTC)
    assert attribute_exit(
        symbol="BTCUSDT",
        avg_entry_price=Decimal("100"),
        exit_at=exit_at,
        our_filled_orders=[_fact()],
    ) == (ExitAttribution.none, None)
    # 같은 공간으로 맞추면 성립한다.
    assert (
        attribute_exit(
            symbol="BTC/USDT",
            avg_entry_price=Decimal("100"),
            exit_at=exit_at,
            our_filled_orders=[_fact()],
        )[0]
        is ExitAttribution.inferred
    )

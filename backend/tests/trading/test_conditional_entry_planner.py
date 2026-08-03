# 조건부 진입 reconcile 계획기의 수량, 발산 차단, 결정론을 검증한다

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from src.strategy.pine_v2.event_loop import PendingOrderSnapshot
from src.trading.services.conditional_entry_planner import (
    RestingConditionalEntry,
    build_conditional_entry_key,
    build_market_converted_entry_key,
    entry_trigger_direction,
    plan_reconcile,
)


def _desired(
    trade_id: str = "entry",
    *,
    direction: Literal["long", "short"] = "long",
    target: Decimal = Decimal("8"),
    stop: Decimal = Decimal("128"),
) -> PendingOrderSnapshot:
    return PendingOrderSnapshot(
        trade_id=trade_id,
        direction=direction,
        target_position=target,
        entry_qty=Decimal("64"),
        stop_price=stop,
        placed_bar=1,
        comment=f"{trade_id} comment",
    )


def _actual(
    trade_id: str = "entry",
    *,
    side: Literal["buy", "sell"] = "buy",
    quantity: Decimal = Decimal("8"),
    stop: Decimal = Decimal("128"),
    trigger_direction: int | None = 1,
    reduce_only: bool = False,
) -> RestingConditionalEntry:
    return RestingConditionalEntry(
        trade_id=trade_id,
        order_id=f"local-{trade_id}",
        exchange_order_id=f"exchange-{trade_id}",
        stop_price=stop,
        quantity=quantity,
        side=side,
        trigger_direction=trigger_direction,
        reduce_only=reduce_only,
    )


def _plan(
    desired: list[PendingOrderSnapshot],
    actual: list[RestingConditionalEntry],
    *,
    current: Decimal = Decimal("0"),
    qty_step: Decimal = Decimal("1"),
    price_tick: Decimal = Decimal("1"),
    reference_price: Decimal | None = None,
    max_breach_pct: Decimal | None = None,
    max_reversal_overshoot_ratio: Decimal | None = None,
    allow_market_conversion: bool = True,
):
    return plan_reconcile(
        desired=desired,
        actual=actual,
        current_position=current,
        qty_step=qty_step,
        price_tick=price_tick,
        reference_price=reference_price,
        max_breach_pct=max_breach_pct,
        max_reversal_overshoot_ratio=max_reversal_overshoot_ratio,
        allow_market_conversion=allow_market_conversion,
    )


def test_new_entry_places_delta_from_current_position() -> None:
    plan = _plan([_desired()], [])

    assert plan.to_cancel == ()
    assert plan.divergences == ()
    assert len(plan.to_place) == 1
    assert plan.to_place[0].side == "buy"
    assert plan.to_place[0].quantity == Decimal("8")


def test_reversal_uses_full_target_delta() -> None:
    """★BL-516 안 3 판정의 수호자 — 수량은 **의도적으로 합쳐진 채** 둔다.

    반전 주문 1건이 청산과 진입을 합쳐 내는 것을 안 3 은 고치지 않기로 판정했다.
    쪼개는 대신 **계측으로 크기를 잰다**(`crosses_zero` / `overshoot_ratio`). 근거:
    leg 분리는 `Order.reduce_only.is_(False)` 술어 4곳
    (`order_repository.py:275/315/347/513`)이 청산 leg 를 reconciler·sweep·janitor·
    진입원장에서 전부 배제해 고아 주문을 낳고, 같은 trigger 가의 조건부 2건은 체결
    순서가 보장되지 않아 `110017 same-side` 를 늘린다.

    ⇒ 이 테스트가 깨지면 안 3 의 핵심 계약이 깨진 것이다. 계측을 더하는 변경이
    수량을 건드리지 않았는지를 여기서 잠근다.
    """
    # 손계산 오라클은 2의 거듭제곱만 쓴다. 정답 16은 오답 8, 24, 0과 서로 다르다.
    plan = _plan([_desired(direction="short", target=Decimal("-8"))], [], current=Decimal("8"))

    assert len(plan.to_place) == 1
    assert plan.to_place[0].side == "sell"
    assert plan.to_place[0].quantity == Decimal("16")


def test_reissued_same_id_at_target_is_quiet_noop() -> None:
    plan = _plan([_desired(target=Decimal("8"))], [], current=Decimal("8"))

    assert plan.to_cancel == ()
    assert plan.to_place == ()
    assert plan.divergences == ()


def test_reissued_same_id_at_target_cancels_stale_resting_order() -> None:
    """수량이 0 이어도 이미 등재된 주문은 걷어내야 한다.

    실포지션이 목표와 같아진 뒤에도 주문을 남겨두면(사용자 수동 거래 등) 그게 체결될 때
    거래소만 목표를 넘어간다. 발주할 것이 없다는 것과 이미 나가 있는 것을 방치해도 된다는
    것은 다른 말이다.
    """
    plan = _plan([_desired(target=Decimal("8"))], [_actual()], current=Decimal("8"))

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert plan.to_place == ()
    # 무음 취소가 아니다 - 사유가 남는다 (payload 는 별도 테스트에서 단정).
    assert [item["reason"] for item in plan.divergences] == ["target_already_met_cancelled"]


def test_matching_desired_and_actual_is_noop() -> None:
    plan = _plan([_desired()], [_actual()])

    assert plan.to_cancel == ()
    assert plan.to_place == ()
    assert plan.divergences == ()


def test_price_change_cancels_and_replaces() -> None:
    plan = _plan([_desired()], [_actual(stop=Decimal("64"))])

    assert [entry.trade_id for entry in plan.to_cancel] == ["entry"]
    assert [entry.trade_id for entry in plan.to_place] == ["entry"]
    assert plan.to_place[0].trigger_price == Decimal("128")


def test_quantity_change_cancels_and_replaces() -> None:
    plan = _plan([_desired()], [_actual(quantity=Decimal("4"))])

    assert [entry.trade_id for entry in plan.to_cancel] == ["entry"]
    assert [entry.trade_id for entry in plan.to_place] == ["entry"]
    assert plan.to_place[0].quantity == Decimal("8")


def test_sub_step_target_change_is_absorbed() -> None:
    # 8과 1/8은 모두 2의 거듭제곱 기반이라 손계산 오라클에 부동소수 오차가 없다.
    plan = _plan([_desired(target=Decimal("8.125"))], [], current=Decimal("8"))

    assert plan.to_cancel == ()
    assert plan.to_place == ()
    assert plan.divergences == ()


def test_disappeared_desired_cancels_actual() -> None:
    plan = _plan([], [_actual()])

    assert [entry.trade_id for entry in plan.to_cancel] == ["entry"]
    assert plan.to_place == ()


def test_entry_side_mismatch_fails_closed() -> None:
    plan = _plan([_desired(target=Decimal("4"))], [], current=Decimal("8"))

    assert plan.to_cancel == ()
    assert plan.to_place == ()
    assert plan.divergences == (
        {
            "trade_id": "entry",
            "reason": "entry_side_mismatch",
            "direction": "long",
            "required_side": "sell",
            # 숫자를 실어야 알림 받은 사람이 초과 규모를 안다.
            "target_position": "4",
            "current_position": "8",
        },
    )


def test_reduce_only_resting_orders_are_never_cancelled() -> None:
    """★손절/TP 레그는 진입이 아니다. 상위 계층 필터가 잘못돼도 지우면 안 된다.

    사용자의 손절을 지우는 것이 이 스프린트가 낼 수 있는 최악의 결함이다.
    미매칭 정리 루프는 소유 판정이 없으므로 마지막 방어선을 계획기에 둔다.
    """
    plan = _plan([], [_actual("stop-loss-leg", side="sell", reduce_only=True)])

    assert plan.to_cancel == ()
    assert [item["reason"] for item in plan.divergences] == ["reduce_only_entry_ignored"]


def test_trigger_direction_mismatch_forces_replacement() -> None:
    """방향이 뒤집힌 채 등재된 주문은 side/수량/가격이 같아도 재등재해야 한다.

    비교 튜플에서 빼면 그런 주문이 영원히 살아남는다 - BL-365 가 다루는 바로 그 축이다.
    """
    plan = _plan([_desired()], [_actual(trigger_direction=2)])

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert [entry.trigger_direction for entry in plan.to_place] == [1]


def test_side_difference_forces_replacement() -> None:
    """수량·가격이 같아도 side 가 다르면 재등재한다."""
    plan = _plan([_desired()], [_actual(side="sell")])

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert [entry.side for entry in plan.to_place] == ["buy"]


def test_planned_order_carries_trigger_direction_for_each_direction() -> None:
    """★배선 검증 - 함수 반환값이 아니라 계획된 주문에 실리는지 본다."""
    long_plan = _plan([_desired("L", direction="long", target=Decimal("8"))], [])
    short_plan = _plan([_desired("S", direction="short", target=Decimal("-8"))], [])

    assert [entry.trigger_direction for entry in long_plan.to_place] == [1]
    assert [entry.trigger_direction for entry in short_plan.to_place] == [2]
    assert [entry.side for entry in short_plan.to_place] == ["sell"]


def test_actual_stop_price_is_normalized_before_comparison() -> None:
    """actual 측 가격도 눈금으로 내려놓고 비교해야 한다.

    한쪽만 정규화하면 눈금 미만 차이가 매 tick 재등재를 유발한다.
    """
    plan = _plan(
        [_desired(stop=Decimal("128"))],
        [_actual(stop=Decimal("128.4"))],
        price_tick=Decimal("1"),
    )

    assert plan.to_cancel == ()
    assert plan.to_place == ()


def test_target_already_met_cancellation_is_reported() -> None:
    """목표 도달로 인한 취소는 무음이면 안 된다.

    엔진 지연으로 형제 레그가 한 tick 사라지는 경우와 구분할 수 없으므로 기록을 남긴다.
    """
    plan = _plan([_desired(target=Decimal("8"))], [_actual()], current=Decimal("8"))

    assert [item["reason"] for item in plan.divergences] == ["target_already_met_cancelled"]
    assert plan.divergences[0]["target_position"] == "8"
    assert plan.divergences[0]["current_position"] == "8"


def test_entry_trigger_direction_matches_breakout_and_breakdown() -> None:
    assert entry_trigger_direction("long") == 1
    assert entry_trigger_direction("short") == 2


def test_reconcile_plan_is_sorted_by_trade_id() -> None:
    plan = _plan(
        [_desired("z"), _desired("b")],
        [_actual("a"), _actual("b", quantity=Decimal("4"))],
    )

    assert [entry.trade_id for entry in plan.to_cancel] == ["a", "b"]
    assert [entry.trade_id for entry in plan.to_place] == ["b", "z"]


def test_divergences_are_deterministic_regardless_of_input_order() -> None:
    """`divergences` 는 최종 정렬을 거치지 않으므로 순회 순서가 곧 출력 순서다.

    발산은 로그와 알림으로 나가므로 같은 상태가 매번 같은 순서로 보고돼야 한다.
    입력을 역순으로 줘도 trade_id 오름차순이어야 한다.
    """
    # 롱 진입인데 실포지션이 목표를 넘어선 상태 -> 둘 다 side mismatch 로 fail-closed.
    plan = _plan(
        [_desired("z", target=Decimal("8")), _desired("b", target=Decimal("8"))],
        [],
        current=Decimal("16"),
    )

    assert [item["trade_id"] for item in plan.divergences] == ["b", "z"]
    assert plan.to_place == ()


def test_sub_minimum_quantity_is_reported_not_silently_dropped() -> None:
    """★목표와 실포지션이 다른데 눈금 미만이면 조용히 넘어가면 안 된다.

    화면엔 "대기 중인 조건부 진입" 이 뜨는데 주문은 영원히 안 나가는 "되는 척" 이 된다.
    실측으로 걸렸다 - 시드 전략의 position_size_pct 가 0.01% 라 수량이 0.00029138 이고
    거래소 스텝은 0.001 이었다.
    """
    plan = _plan(
        [_desired(target=Decimal("0.00029138"))],
        [],
        current=Decimal("0"),
        qty_step=Decimal("0.001"),
    )

    assert plan.to_place == ()
    assert [item["reason"] for item in plan.divergences] == ["below_exchange_minimum"]
    assert plan.divergences[0]["target_position"] == "0.00029138"


def test_target_already_met_stays_a_quiet_noop() -> None:
    """음성 대조 - 목표와 실포지션이 같으면 발산이 아니라 정상 no-op 이다."""
    plan = _plan(
        [_desired(target=Decimal("8"))], [], current=Decimal("8"), qty_step=Decimal("0.001")
    )

    assert plan.to_place == ()
    assert plan.divergences == ()


def test_breached_trigger_without_resting_converts_to_market() -> None:
    """resting 주문 없이 이미 돌파됐으면 백테스트의 다음 시가 체결로 근사한다."""
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [],
        reference_price=Decimal("110"),
    )

    assert plan.to_cancel == ()
    assert plan.divergences == ()
    assert len(plan.to_place) == 1
    assert plan.to_place[0].as_market is True


def test_allow_market_conversion_false_keeps_legacy_behaviour() -> None:
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [],
        reference_price=Decimal("110"),
        allow_market_conversion=False,
    )

    assert plan.to_cancel == ()
    assert plan.to_place == ()
    assert plan.divergences[0]["reason"] == "trigger_already_breached"
    assert plan.divergences[0]["had_resting"] is False


def test_conditional_and_market_keys_share_longer_namespace_boundary() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    session_id = uuid4()
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    trade_id = "x" * 132

    conditional_key = build_conditional_entry_key(
        session_id, trade_id, bar_time, Decimal("100"), Decimal("1")
    )
    market_key = build_market_converted_entry_key(
        session_id, trade_id, bar_time, Decimal("100"), Decimal("1")
    )

    assert (conditional_key is None) == (market_key is None)


def test_breached_trigger_with_resting_cancels_and_does_not_convert() -> None:
    """resting stop이 있으면 거래소 트리거 경합을 피하려 기존 취소 동작을 유지한다."""
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [_actual(stop=Decimal("100"))],
        reference_price=Decimal("110"),
    )

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert plan.to_place == ()
    assert plan.divergences[0]["reason"] == "trigger_already_breached"
    assert plan.divergences[0]["had_resting"] is True


def test_breached_trigger_with_unfireable_resting_converts_to_market() -> None:
    """[BL-589] 대기 주문이 **발화할 수 없었으면** 이중 진입 위험이 없다 — 시장가로 전환한다.

    2026-08-03 소크를 T0+65분에 죽인 형태다. 피벗이 내려가 새 트리거(100)가 현재가(110)
    아래라 stop 으로 못 거는데, 올라가 있던 대기 주문의 트리거는 120 이라 **한 번도 닿은 적이
    없다**. 그런데 계획기는 「대기 주문이 있다」는 이유만으로 시장가 전환을 끄고 그 주문을
    취소해버렸다. 시뮬은 `low <= stop` 으로 이미 진입을 잡았으므로 엔진 롱 / 거래소 숏이 되고
    `direction` 발산 2회 연속으로 세션이 fail-closed 됐다.

    PR #493 이 배제한 근거는 "거래소가 이미 그 주문을 트리거했을 확률이 높아 취소+시장가는
    이중 진입이 된다" 였다. 그 확률은 **대기 주문 자신의 트리거가 뚫렸을 때만** 0 이 아니다.
    """
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [_actual(stop=Decimal("120"))],
        reference_price=Decimal("110"),
    )

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert len(plan.to_place) == 1
    assert plan.to_place[0].as_market is True
    assert plan.divergences == ()


def test_unfireable_resting_still_dropped_when_conversion_disabled() -> None:
    """전환이 꺼져 있으면(기준가가 거래소 last 가 아니면) 발화 불가여도 기존 드롭을 유지한다.

    ★음성 대조다 — 위 전환이 `allow_market_conversion` 을 우회해서 열린 게 아님을 보인다.
    """
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [_actual(stop=Decimal("120"))],
        reference_price=Decimal("110"),
        allow_market_conversion=False,
    )

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert plan.to_place == ()
    assert plan.divergences[0]["reason"] == "trigger_already_breached"
    assert plan.divergences[0]["had_resting"] is True


def test_breach_drop_records_why_the_resting_order_blocked_conversion() -> None:
    """드롭이 남는 두 갈래를 로그·계측에서 가를 수 있어야 한다.

    `had_resting` 만으로는 「대기 주문이 발화할 수 있어서 막았다」와 「전환 자체가 꺼져
    있었다」가 구별되지 않는다. 앞엣것은 정당한 보호이고 뒤엣것은 기준가 열화다.
    [BL-589] 회차에서 이 구별이 없어 11건의 `breach_with_resting` 중 몇 건이 실제 위험이었는지
    사후에 셀 수 없었다.
    """
    fireable = _plan(
        [_desired(stop=Decimal("100"))],
        [_actual(stop=Decimal("100"))],
        reference_price=Decimal("110"),
    )
    conversion_off = _plan(
        [_desired(stop=Decimal("100"))],
        [_actual(stop=Decimal("120"))],
        reference_price=Decimal("110"),
        allow_market_conversion=False,
    )

    assert fireable.divergences[0]["resting_could_have_fired"] is True
    assert conversion_off.divergences[0]["resting_could_have_fired"] is False


def test_market_conversion_never_reuses_a_resting_stop_order() -> None:
    """★눈금이 굵으면 시장가 의도가 대기 stop 주문과 '일치' 로 접힐 수 있다.

    `price_tick=10` 이면 desired stop 100 과 resting stop 108 이 둘 다 100 으로 정규화된다.
    side·수량·trigger_direction 까지 같으면 등가 판정에 걸려 **아무것도 취소하지 않고 아무것도
    등재하지 않는다** — 시장가로 나갔어야 할 진입이 조용히 사라지고 대기 stop 만 남는다.
    `as_market` 은 등가 비교 축에 없으므로, 전환이 결정된 leg 는 항상 재등재해야 한다.

    ★이 구멍은 수리 **전에는 도달 불가**였다(전환과 대기 주문이 공존할 수 없었다).
    사전등록에는 없었고 구현 중 발견했다.
    """
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [_actual(stop=Decimal("108"))],
        reference_price=Decimal("105"),
        price_tick=Decimal("10"),
    )

    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    assert len(plan.to_place) == 1
    assert plan.to_place[0].as_market is True


def test_breach_within_cap_still_converts() -> None:
    """돌파폭이 상한과 정확히 같으면 허용한다(M9 경계)."""
    plan = _plan(
        [_desired(stop=Decimal("9995"))],
        [],
        reference_price=Decimal("10000"),
        max_breach_pct=Decimal("0.05"),
    )

    assert len(plan.to_place) == 1
    assert plan.to_place[0].as_market is True


def test_breach_exceeding_cap_is_not_placed() -> None:
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [],
        reference_price=Decimal("101"),
        max_breach_pct=Decimal("0.5"),
    )

    assert plan.to_place == ()
    assert plan.divergences[0]["reason"] == "breach_exceeds_cap"
    assert plan.divergences[0]["breach_pct"] == "0.9900990099009900990099009901"
    assert plan.divergences[0]["max_breach_pct"] == "0.5"


def test_cap_none_means_unlimited() -> None:
    plan = _plan(
        [_desired(stop=Decimal("100"))],
        [],
        reference_price=Decimal("200"),
        max_breach_pct=None,
    )

    assert len(plan.to_place) == 1
    assert plan.to_place[0].as_market is True


def test_converted_entry_still_respects_side_mismatch_guard() -> None:
    plan = _plan(
        [_desired(target=Decimal("4"), stop=Decimal("100"))],
        [],
        current=Decimal("8"),
        reference_price=Decimal("110"),
    )

    assert plan.to_place == ()
    assert [item["reason"] for item in plan.divergences] == ["entry_side_mismatch"]


def test_converted_entry_still_respects_below_exchange_minimum() -> None:
    plan = _plan(
        [_desired(target=Decimal("0.0002"), stop=Decimal("100"))],
        [],
        qty_step=Decimal("0.001"),
        reference_price=Decimal("110"),
    )

    assert plan.to_place == ()
    assert [item["reason"] for item in plan.divergences] == ["below_exchange_minimum"]


def test_reachable_trigger_still_places_conditional() -> None:
    """음성 대조 - 정상 방향이면 그대로 발주한다(과잉차단 아님)."""
    long_ok = _plan([_desired(stop=Decimal("128"))], [], reference_price=Decimal("64"))
    short_ok = _plan(
        [_desired(direction="short", target=Decimal("-8"), stop=Decimal("64"))],
        [],
        reference_price=Decimal("128"),
    )

    assert [e.trade_id for e in long_ok.to_place] == ["entry"]
    assert [e.trade_id for e in short_ok.to_place] == ["entry"]
    assert long_ok.to_place[0].as_market is False
    assert short_ok.to_place[0].as_market is False
    assert long_ok.divergences == () and short_ok.divergences == ()


def test_reference_price_omitted_keeps_previous_behaviour() -> None:
    """참조가 미지정이면 검사를 건너뛴다 - 기존 호출자 무영향."""
    plan = _plan([_desired(direction="short", target=Decimal("-8"), stop=Decimal("128"))], [])

    assert [e.trade_id for e in plan.to_place] == ["entry"]
    assert plan.divergences == ()


# ── BL-516 안 3: 반전 계측 + 선택적 캡 ──────────────────────────────────────


def test_reversal_is_labelled_with_its_overshoot_size() -> None:
    """반전은 부호 교차로 판정하고 크기는 비율로 잰다. 목표 -8 / 보유 +8 -> 16 / 8 = 2."""
    plan = _plan([_desired(direction="short", target=Decimal("-8"))], [], current=Decimal("8"))

    planned = plan.to_place[0]
    assert planned.crosses_zero is True
    assert planned.overshoot_ratio == Decimal("2")
    # 체결 후 포지션은 -8 이므로 크기 8 — 주문수량 16 과 다르다(그래서 tpSize 가 어긋난다).
    assert planned.resulting_position_qty == Decimal("8")


def test_flat_entry_is_not_a_reversal_and_scores_exactly_one() -> None:
    """대조군 — 무포지션에서의 진입은 부호 교차가 아니고 비율이 정확히 1.0 이다."""
    plan = _plan([_desired(target=Decimal("8"))], [], current=Decimal("0"))

    planned = plan.to_place[0]
    assert planned.crosses_zero is False
    assert planned.overshoot_ratio == Decimal("1")
    assert planned.resulting_position_qty == planned.quantity == Decimal("8")


def test_resulting_position_uses_normalized_fill_not_raw_target() -> None:
    """★눈금 미정렬 목표에서 `abs(target_position)` 을 쓰면 순수 진입까지 불일치로 보인다.

    percent_of_equity 사이징은 소수 20자리를 만든다(`event_loop.py` 주석의 실측
    0.00029537036490054884). 발주 수량은 `qty_step` 으로 절삭되므로 체결 후 포지션은
    목표가 아니라 **절삭된 수량**이다. 그 둘을 혼동하면 tpSize 게이트가 반전이 아닌
    진입에서도 TP 를 떨어뜨린다.
    """
    plan = _plan([_desired(target=Decimal("0.02953691"))], [], qty_step=Decimal("0.001"))

    planned = plan.to_place[0]
    assert planned.quantity == Decimal("0.029")
    assert planned.resulting_position_qty == Decimal("0.029")
    assert planned.crosses_zero is False


def test_reversal_overshoot_cap_drops_the_leg_and_cancels_resting() -> None:
    """캡 활성 — 초과 반전은 등재하지 않고, 같은 의도의 resting 도 걷어낸다.

    남겨두면 그게 체결돼 방금 거부한 반전을 그대로 실행한다.
    """
    plan = _plan(
        [_desired(direction="short", target=Decimal("-8"), stop=Decimal("64"))],
        [_actual(side="sell", quantity=Decimal("16"), stop=Decimal("64"), trigger_direction=2)],
        current=Decimal("8"),
        max_reversal_overshoot_ratio=Decimal("1.5"),
    )

    assert plan.to_place == ()
    assert [entry.order_id for entry in plan.to_cancel] == ["local-entry"]
    divergence = plan.divergences[0]
    assert divergence["reason"] == "reversal_overshoot_exceeds_cap"
    assert divergence["overshoot_ratio"] == "2"
    assert divergence["max_reversal_overshoot_ratio"] == "1.5"


def test_reversal_overshoot_cap_at_the_boundary_still_places() -> None:
    """경계는 초과가 아니다 — 비율 2 에 캡 2 면 그대로 등재한다."""
    plan = _plan(
        [_desired(direction="short", target=Decimal("-8"))],
        [],
        current=Decimal("8"),
        max_reversal_overshoot_ratio=Decimal("2"),
    )

    assert [entry.trade_id for entry in plan.to_place] == ["entry"]
    assert plan.divergences == ()


def test_reversal_overshoot_cap_defaults_to_disabled() -> None:
    """★회귀 0 — 캡 미지정이면 비율 4 짜리 반전도 그대로 나간다(기존 동작 불변)."""
    plan = _plan([_desired(direction="short", target=Decimal("-8"))], [], current=Decimal("24"))

    planned = plan.to_place[0]
    assert planned.quantity == Decimal("32")
    assert planned.overshoot_ratio == Decimal("4")
    assert plan.divergences == ()


def test_cap_never_blocks_a_non_reversal_entry() -> None:
    """캡은 반전 전용이다 — 같은 방향 증량은 비율이 1 이하라 캡과 무관하다."""
    plan = _plan(
        [_desired(target=Decimal("8"))],
        [],
        current=Decimal("4"),
        max_reversal_overshoot_ratio=Decimal("1"),
    )

    planned = plan.to_place[0]
    assert planned.crosses_zero is False
    assert planned.quantity == Decimal("4")
    assert plan.divergences == ()


# ── BL-562: 반전 계측/캡이 "등재 시점 근사" 라는 것의 경계 ──────────────────


def test_position_drift_forces_a_fresh_replacement_with_recomputed_reversal_facts() -> None:
    """★BL-562 의 노출 폭을 재는 상한 — 드리프트는 보통 **다음 tick 에 재등재로 걷힌다**.

    `crosses_zero`/`overshoot_ratio`/`resulting_position_qty` 는 등재 시점 값이지만
    `plan_reconcile` 은 **매 tick 실포지션으로 다시 돈다**. 수량은
    `|target - current_position|` 이라 포지션이 움직이면 비교 튜플(`:542-547`)이
    어긋나고, 그러면 resting 을 걷고 **새 값으로** 재등재한다.

    보유 0 에서 목표 -8 로 등재(수량 8, 반전 아님) -> 보유 +8 로 드리프트하면
    수량 16 · 반전 · 체결 후 8 로 **다시 계산돼** 나간다.
    """
    placed_when_flat = _plan(
        [_desired(direction="short", target=Decimal("-8"))], [], current=Decimal("0")
    )
    assert placed_when_flat.to_place[0].quantity == Decimal("8")
    assert placed_when_flat.to_place[0].crosses_zero is False

    drifted = _plan(
        [_desired(direction="short", target=Decimal("-8"))],
        [_actual(side="sell", quantity=Decimal("8"), trigger_direction=2)],
        current=Decimal("8"),
    )

    assert [entry.order_id for entry in drifted.to_cancel] == ["local-entry"]
    replaced = drifted.to_place[0]
    assert replaced.quantity == Decimal("16")
    assert replaced.crosses_zero is True
    assert replaced.resulting_position_qty == Decimal("8")


def test_drift_that_leaves_the_compare_tuple_intact_keeps_the_stale_leg_resting() -> None:
    """★BL-562 의 잔여 노출 — 비교 튜플이 그대로면 재등재가 없어 옛 판정이 살아남는다.

    비교 대상은 `(side, quantity, stop_price, trigger_direction)` 뿐이고
    `crosses_zero`/`resulting_position_qty` 는 **거기 없다**. 목표와 실포지션이 같은
    폭으로 움직이면 수량이 그대로라 resting 이 유지되는데, 그 사이 게이트 B 판정은
    뒤집힌다 — flat 진입(수량 1 == 체결 후 1, TP 유지)으로 등재된 leg 가 드리프트 후엔
    반전(수량 1 != 체결 후 0.5, TP 드롭 대상)이 된다.

    ★그래도 캡/게이트 B 를 체결 시점으로 옮길 수는 없다 — 주문은 이미 거래소에 있고
    `tpSize` 는 등재할 때 확정된다. 이 테스트는 그 사실을 고정하는 것이지 고칠 지점을
    가리키는 것이 아니다.
    """
    fresh = _plan(
        [_desired(target=Decimal("0.5"))],
        [],
        current=Decimal("-0.5"),
        qty_step=Decimal("0.1"),
    )
    planned_now = fresh.to_place[0]
    assert planned_now.quantity == Decimal("1.0")
    assert planned_now.crosses_zero is True
    # 수량 1.0 != 체결 후 0.5 -> 지금 등재한다면 게이트 B 가 TP 를 드롭한다.
    assert planned_now.resulting_position_qty == Decimal("0.5")

    kept = _plan(
        [_desired(target=Decimal("0.5"))],
        [_actual(quantity=Decimal("1"))],
        current=Decimal("-0.5"),
        qty_step=Decimal("0.1"),
    )

    # 튜플이 일치해 아무 일도 일어나지 않는다 = 옛 tpSize 가 거래소에 그대로 남는다.
    assert kept.to_place == ()
    assert kept.to_cancel == ()
    assert kept.divergences == ()


def test_exit_levels_pass_through_the_planner_untouched() -> None:
    """계획기는 브래킷을 **판단하지 않는다** — 그대로 통과시킨다(순수 함수 유지)."""
    desired = PendingOrderSnapshot(
        trade_id="entry",
        direction="long",
        target_position=Decimal("8"),
        entry_qty=Decimal("8"),
        stop_price=Decimal("128"),
        placed_bar=1,
        take_profit=Decimal("192"),
        stop_loss=Decimal("64"),
        trailing_stop=Decimal("4"),
    )

    planned = _plan([desired], []).to_place[0]

    assert planned.take_profit == Decimal("192")
    assert planned.stop_loss == Decimal("64")
    assert planned.trailing_stop == Decimal("4")


def test_exit_levels_default_to_none_when_engine_supplies_none() -> None:
    """회귀 0 — 엔진이 안 주면 세 필드는 None 이다(조건부 진입의 현재 상태)."""
    planned = _plan([_desired()], []).to_place[0]

    assert (planned.take_profit, planned.stop_loss, planned.trailing_stop) == (None, None, None)

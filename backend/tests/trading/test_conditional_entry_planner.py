# 조건부 진입 reconcile 계획기의 수량, 발산 차단, 결정론을 검증한다

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from src.strategy.pine_v2.event_loop import PendingOrderSnapshot
from src.trading.services.conditional_entry_planner import (
    RestingConditionalEntry,
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
):
    return plan_reconcile(
        desired=desired,
        actual=actual,
        current_position=current,
        qty_step=qty_step,
        price_tick=price_tick,
    )


def test_new_entry_places_delta_from_current_position() -> None:
    plan = _plan([_desired()], [])

    assert plan.to_cancel == ()
    assert plan.divergences == ()
    assert len(plan.to_place) == 1
    assert plan.to_place[0].side == "buy"
    assert plan.to_place[0].quantity == Decimal("8")


def test_reversal_uses_full_target_delta() -> None:
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

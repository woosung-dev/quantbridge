# exit_orders.py 의 Wave1 frozen 계약(enum value/우선순위/fill_type) 을 고정하는 lock 테스트.
"""T0-pine-oco C1 — exit-order kind + same-bar fill-priority SSOT 계약 lock.

이 모듈은 Wave 1 라이브-주문 워커가 **import** (편집 X) 해 백테스트 sim 과
라이브 주문이 동일 enum + 동시-체결 규칙을 공유하는 frozen 계약이다.
value 문자열·우선순위 순서·fill_type 매핑이 바뀌면 백테스트↔라이브 정합이
깨지므로 본 테스트가 의도적으로 엄격하게 고정한다.
"""
from __future__ import annotations

from src.strategy.pine_v2.exit_orders import (
    SAME_BAR_FILL_PRIORITY,
    ExitOrderKind,
    fill_type_for,
    pessimistic_fill_order,
)


def test_exit_order_kind_values_are_frozen() -> None:
    # Wave1 라이브 주문이 의존하는 wire value — 변경 금지.
    assert ExitOrderKind.TAKE_PROFIT.value == "take_profit"
    assert ExitOrderKind.STOP_LOSS.value == "stop_loss"
    assert ExitOrderKind.TRAILING_STOP.value == "trailing_stop"
    # str Enum — value 가 곧 문자열.
    assert ExitOrderKind.STOP_LOSS == "stop_loss"


def test_same_bar_fill_priority_is_sl_first_pessimistic() -> None:
    # 동시-trigger 시 SL 우선 = pessimistic = 실거래 최악가정 일치.
    assert SAME_BAR_FILL_PRIORITY == (
        ExitOrderKind.STOP_LOSS,
        ExitOrderKind.TRAILING_STOP,
        ExitOrderKind.TAKE_PROFIT,
    )


def test_fill_type_for_routes_tp_maker_sl_trail_taker() -> None:
    # cost SSOT 브릿지: TP=resting limit→maker, SL/Trail=trigger→taker.
    assert fill_type_for(ExitOrderKind.TAKE_PROFIT) == "maker"
    assert fill_type_for(ExitOrderKind.STOP_LOSS) == "taker"
    assert fill_type_for(ExitOrderKind.TRAILING_STOP) == "taker"


def test_pessimistic_fill_order_sorts_by_priority() -> None:
    # 입력 순서와 무관하게 SAME_BAR_FILL_PRIORITY 순으로 정렬.
    unsorted = [ExitOrderKind.TAKE_PROFIT, ExitOrderKind.STOP_LOSS]
    assert pessimistic_fill_order(unsorted) == [
        ExitOrderKind.STOP_LOSS,
        ExitOrderKind.TAKE_PROFIT,
    ]


def test_pessimistic_fill_order_preserves_duplicates_stably() -> None:
    # 같은 kind 중복은 보존 (여러 엔트리의 동일 leg).
    kinds = [
        ExitOrderKind.TAKE_PROFIT,
        ExitOrderKind.STOP_LOSS,
        ExitOrderKind.TAKE_PROFIT,
    ]
    assert pessimistic_fill_order(kinds) == [
        ExitOrderKind.STOP_LOSS,
        ExitOrderKind.TAKE_PROFIT,
        ExitOrderKind.TAKE_PROFIT,
    ]

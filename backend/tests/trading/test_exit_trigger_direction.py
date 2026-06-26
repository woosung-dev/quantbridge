# Wave 2 — trigger_direction_for 순수함수 (ccxt v5 rise/fall SSOT) 검증.
"""ccxt 4.5.49 bybit create_order_request line 4115-4122 정합:
- triggerDirection 1 = 가격 RISE 시 트리거, 2 = FALL 시 트리거.
- exit 주문 side 기준: closing-long(sell) SL=2/TP=1, closing-short(buy) SL=1/TP=2.
- TRAILING_STOP 은 STOP_LOSS 와 동일 방향 규칙.
"""
from __future__ import annotations

from src.strategy.pine_v2.exit_orders import ExitOrderKind
from src.trading.models import OrderSide


def test_closing_long_stop_loss_triggers_on_fall() -> None:
    # long 청산 = sell. SL 은 가격이 stop 아래로 FALL 시 → 2.
    from src.strategy.pine_v2.exit_order_mapping import trigger_direction_for

    assert trigger_direction_for(OrderSide.sell, ExitOrderKind.STOP_LOSS) == 2


def test_closing_short_stop_loss_triggers_on_rise() -> None:
    # short 청산 = buy. SL 은 가격이 stop 위로 RISE 시 → 1.
    from src.strategy.pine_v2.exit_order_mapping import trigger_direction_for

    assert trigger_direction_for(OrderSide.buy, ExitOrderKind.STOP_LOSS) == 1


def test_closing_long_take_profit_triggers_on_rise() -> None:
    # long 청산 TP = sell. TP 는 가격이 limit 위로 RISE 시 → 1.
    from src.strategy.pine_v2.exit_order_mapping import trigger_direction_for

    assert trigger_direction_for(OrderSide.sell, ExitOrderKind.TAKE_PROFIT) == 1


def test_closing_short_take_profit_triggers_on_fall() -> None:
    # short 청산 TP = buy. TP 는 가격이 limit 아래로 FALL 시 → 2.
    from src.strategy.pine_v2.exit_order_mapping import trigger_direction_for

    assert trigger_direction_for(OrderSide.buy, ExitOrderKind.TAKE_PROFIT) == 2


def test_trailing_stop_matches_stop_loss_direction() -> None:
    # TRAILING_STOP = STOP_LOSS 방향 규칙 동일.
    from src.strategy.pine_v2.exit_order_mapping import trigger_direction_for

    assert trigger_direction_for(OrderSide.sell, ExitOrderKind.TRAILING_STOP) == 2
    assert trigger_direction_for(OrderSide.buy, ExitOrderKind.TRAILING_STOP) == 1

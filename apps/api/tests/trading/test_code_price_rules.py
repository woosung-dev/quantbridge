"""중간 tick VWAP에서도 native 활성 시 손익분기·추가 손실 상한을 보장한다."""

from decimal import Decimal as D

import pytest

from src.trading.code_price_rules import protection_prices


@pytest.mark.parametrize(
    "direction,stop,activation,expected_be,expected_active",
    [
        ("long", "97.828", "104.094", "100.1", "104.2"),
        ("short", "102.272", "96.006", "100.0", "95.9"),
    ],
)
def test_mid_tick_entry_does_not_start_trailing_on_loss_side(
    direction, stop, activation, expected_be, expected_active
):
    result = protection_prices(
        direction=direction,
        entry_price=D("100.05"),
        stop_loss=D(stop),
        tick=D("0.1"),
        distance=D("4.044"),
        activation=D(activation),
        breakeven_required=False,
    )
    assert result["breakeven_price"] == expected_be
    assert D(result["active_price"]) == D(expected_active)
    assert D(result["trailing_distance"]) == D("4.1")
    initial = D(result["native_initial_stop"])
    assert initial >= D("100.05") if direction == "long" else initial <= D("100.05")
    assert D(result["activation_delay"]) < D("0.2")


@pytest.mark.parametrize("direction", ["long", "short"])
def test_outward_sl_adds_less_than_one_tick_and_be_stop_never_crosses_entry(direction):
    for offset in range(1, 100):
        entry = D(100) + D(offset) / 1000
        sign = D(1) if direction == "long" else D(-1)
        requested_stop = entry - sign * D("2.211")
        initial = protection_prices(
            direction=direction,
            entry_price=entry,
            stop_loss=requested_stop,
            tick=D("0.1"),
            distance=None,
            activation=None,
            breakeven_required=False,
        )
        loss_addition = sign * (requested_stop - D(initial["stop_loss"]))
        assert 0 <= loss_addition < D("0.1")
        moved = protection_prices(
            direction=direction,
            entry_price=entry,
            stop_loss=entry,
            tick=D("0.1"),
            distance=None,
            activation=None,
            breakeven_required=True,
        )
        assert sign * (D(moved["stop_loss"]) - entry) >= 0

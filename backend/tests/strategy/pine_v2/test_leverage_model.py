# Pine v2 레버리지 증거금과 isolated 청산가의 손계산 회귀 테스트.

from __future__ import annotations

import math

import pytest

from src.strategy.pine_v2.leverage_model import (
    is_leverage_active,
    liquidation_price,
    margin_available_ok,
    required_margin,
)


@pytest.mark.parametrize(
    ("direction", "leverage", "expected"),
    [
        ("long", 10.0, 90.5),
        ("short", 10.0, 109.5),
        ("long", 2.0, 50.5),
        ("short", 2.0, 149.5),
        ("long", 2.5, 60.5),
    ],
)
def test_liquidation_price_hand_computed(
    direction: str, leverage: float, expected: float
) -> None:
    assert liquidation_price(
        entry_price=100.0,
        direction=direction,  # type: ignore[arg-type]
        leverage=leverage,
    ) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("leverage", "expected"),
    [
        (1.0, False),
        (0.999, False),
        (1.0000001, True),
        (math.inf, False),
        (math.nan, False),
    ],
)
def test_is_leverage_active(leverage: float, expected: bool) -> None:
    assert is_leverage_active(leverage) is expected


def test_required_margin() -> None:
    assert required_margin(qty=2.0, price=100.0, leverage=10.0) == 20.0
    assert math.isinf(required_margin(qty=2.0, price=100.0, leverage=0.0))


def test_margin_available_ok_includes_buffer_boundary() -> None:
    assert margin_available_ok(required=95.0, available=100.0)
    assert not margin_available_ok(required=95.01, available=100.0)


@pytest.mark.parametrize(
    ("entry_price", "leverage"),
    [(0.0, 10.0), (100.0, 0.0), (math.nan, 10.0)],
)
def test_liquidation_price_returns_none_for_invalid_inputs(
    entry_price: float, leverage: float
) -> None:
    assert liquidation_price(
        entry_price=entry_price,
        direction="long",
        leverage=leverage,
    ) is None

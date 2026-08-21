# Pine 기본 주문 수량 해석의 우선순위와 fail-closed 계약을 고정한다.
"""sizing 모듈의 순수 기본 주문 수량 해석 회귀 테스트."""

from __future__ import annotations

import pytest

from src.strategy.pine_v2.sizing import extract_pine_default_qty, resolve_default_qty

_PINE_FULL_QTY = """//@version=5
strategy("Full", default_qty_type=strategy.cash, default_qty_value=123.45)
"""
_PINE_BARE = """//@version=5
strategy("Bare")
"""
_PINE_TYPE_ONLY = """//@version=5
strategy("Type only", default_qty_type=strategy.fixed)
"""
_PINE_INDICATOR = """//@version=5
indicator("Indicator")
"""
_PINE_INVALID_QTY_VALUE = """//@version=5
strategy("Invalid qty", default_qty_type=strategy.cash, default_qty_value=not_a_number)
"""


def test_pine_explicit_qty_overrides_form_and_live() -> None:
    """Pine의 완전한 기본 수량 선언은 form과 live 값을 모두 이긴다."""
    resolved = resolve_default_qty(
        _PINE_FULL_QTY,
        initial_capital=10_000.0,
        form_default_qty_type="strategy.fixed",
        form_default_qty_value=3.0,
        live_position_size_pct=55.0,
    )

    assert resolved == ("strategy.cash", 123.45)


def test_form_qty_overrides_live_when_pine_is_silent() -> None:
    """Pine 미명시 시 완전한 form 수량이 live 비율보다 우선한다."""
    resolved = resolve_default_qty(
        _PINE_BARE,
        initial_capital=10_000.0,
        form_default_qty_type="strategy.fixed",
        form_default_qty_value=3.0,
        live_position_size_pct=55.0,
    )

    assert resolved == ("strategy.fixed", 3.0)


def test_live_pct_becomes_percent_of_equity_float() -> None:
    """Pine·form 미명시 시 live 비율을 float percent_of_equity로 해석한다."""
    resolved = resolve_default_qty(
        _PINE_BARE,
        initial_capital=10_000.0,
        live_position_size_pct=12,
    )

    assert resolved == ("strategy.percent_of_equity", 12.0)
    assert isinstance(resolved[1], float)


def test_returns_none_pair_when_all_sources_are_silent() -> None:
    """세 수량 소스가 모두 없으면 회귀 호환 fallback 입력을 반환한다."""
    assert resolve_default_qty(_PINE_BARE, initial_capital=10_000.0) == (None, None)


def test_live_pct_without_initial_capital_fails_closed() -> None:
    """BL-479: 자본 기준선 없는 live 비율은 qty=1.0 fallback 전에 차단한다."""
    with pytest.raises(ValueError, match="BL-479"):
        resolve_default_qty(
            _PINE_BARE,
            initial_capital=None,
            live_position_size_pct=12.0,
        )


def test_missing_initial_capital_without_live_pct_returns_none_pair() -> None:
    """자본과 live 비율이 모두 없으면 BL-479 예외가 아닌 정상 fallback 입력이다."""
    assert resolve_default_qty(_PINE_BARE, initial_capital=None) == (None, None)


@pytest.mark.parametrize(
    ("form_qty_type", "form_qty_value"),
    [
        ("strategy.fixed", None),
        (None, 3.0),
    ],
)
def test_partial_form_qty_falls_through_to_live(
    form_qty_type: str | None,
    form_qty_value: float | None,
) -> None:
    """form은 type과 value가 함께 있어야 하며, 일부만 있으면 live 단계로 내려간다."""
    resolved = resolve_default_qty(
        _PINE_BARE,
        initial_capital=10_000.0,
        form_default_qty_type=form_qty_type,
        form_default_qty_value=form_qty_value,
        live_position_size_pct=17.5,
    )

    assert resolved == ("strategy.percent_of_equity", 17.5)


def test_partial_pine_qty_falls_through_to_form() -> None:
    """Pine도 type과 value가 함께 있어야 하며, 일부 선언은 form을 막지 않는다."""
    resolved = resolve_default_qty(
        _PINE_TYPE_ONLY,
        initial_capital=10_000.0,
        form_default_qty_type="strategy.fixed",
        form_default_qty_value=3.0,
    )

    assert resolved == ("strategy.fixed", 3.0)


def test_extract_pine_default_qty_returns_none_for_indicator() -> None:
    """strategy 선언이 아닌 script는 기본 수량을 제공하지 않는다."""
    assert extract_pine_default_qty(_PINE_INDICATOR) == (None, None)


def test_extract_pine_default_qty_keeps_type_and_drops_unparseable_value() -> None:
    """관측값: 숫자가 아닌 default_qty_value는 예외 대신 None으로 해석한다."""
    assert extract_pine_default_qty(_PINE_INVALID_QTY_VALUE) == ("strategy.cash", None)

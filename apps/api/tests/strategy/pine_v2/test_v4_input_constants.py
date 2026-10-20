"""실제 수집 지표가 사용한 v4 input 타입 상수와 기존 수학 함수 별칭 회귀."""

from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical


def _candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10.0] * 4,
            "high": [12.0] * 4,
            "low": [8.0] * 4,
            "close": [9.0, 11.0, 9.0, 11.0],
            "volume": [1.0] * 4,
        },
        index=pd.date_range("2026-01-01", periods=4, freq="h", tz="UTC"),
    )


@pytest.mark.parametrize(
    "constant,default,expected",
    [
        ("integer", "10", [10] * 4),
        ("float", "2.5", [2.5] * 4),
        ("bool", "false", [False] * 4),
        ("source", "close", [9.0, 11.0, 9.0, 11.0]),
    ],
)
def test_v4_input_type_constant_preserves_default(constant, default, expected):
    source = f'//@version=4\nstudy("legacy inputs")\nx = input(title="value", type=input.{constant}, defval={default})\n'
    coverage = analyze_coverage(source)
    assert coverage.is_runnable, coverage.all_unsupported
    assert f"input.{constant}" in coverage.used_attributes
    assert run_historical(source, _candles()).var_series["x"] == expected


def test_input_type_constant_does_not_create_unknown_function_or_attribute_support():
    unknown = analyze_coverage('//@version=4\nstudy("unknown")\nx = input(1, type=input.unknown)\n')
    assert unknown.unsupported_attributes == ("input.unknown",)
    invalid_call = analyze_coverage('//@version=4\nstudy("unknown")\nx = input.integer(1)\n')
    assert invalid_call.unsupported_functions == ("input.integer",)
    modern = '//@version=5\nindicator("modern")\nx = input.bool(true)\ny = input.float(2.5)\n'
    assert analyze_coverage(modern).is_runnable
    result = run_historical(modern, _candles())
    assert result.var_series["x"] == [True] * 4
    assert result.var_series["y"] == [2.5] * 4


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("cross(close, open)", [False, True, True, True]),
        ("floor(close - 10.5)", [-2, 0, -2, 0]),
    ],
)
def test_v4_alias_uses_existing_numerical_implementation(expression, expected):
    source = f'//@version=4\nstudy("legacy aliases")\nx = {expression}\n'
    assert analyze_coverage(source).is_runnable
    assert run_historical(source, _candles()).var_series["x"] == expected


@pytest.mark.parametrize(
    "constant",
    [
        "format.price",
        "plot.style_line",
        "plot.style_linebr",
        "plot.style_circles",
        "plot.style_cross",
    ],
)
def test_collected_display_constants_are_explicit_and_runtime_safe(constant):
    source = f'//@version=4\nstudy("display")\nx = {constant}\nplot(close, style=plot.style_line)\n'
    assert analyze_coverage(source).is_runnable
    assert len(run_historical(source, _candles()).var_series["x"]) == 4


@pytest.mark.parametrize("constant", ["format.unknown", "plot.style_unknown"])
def test_unknown_display_constants_remain_unsupported(constant):
    source = f'//@version=4\nstudy("unknown display")\nx = {constant}\n'
    assert analyze_coverage(source).unsupported_attributes == (constant,)


def test_bare_stdev_reuses_population_standard_deviation():
    source = '//@version=4\nstudy("stdev")\nx = stdev(close, 2)\n'
    assert analyze_coverage(source).is_runnable
    values = run_historical(source, _candles()).var_series["x"]
    assert values[1:] == [1.0, 1.0, 1.0]


def test_v4_true_range_and_namespaced_attribute_share_gap_semantics():
    data = _candles()
    data.iloc[1] = [19.0, 20.0, 18.0, 19.0, 1.0]
    source = '//@version=4\nstudy("true range")\nx = tr\ny = ta.tr\n'
    assert analyze_coverage(source).is_runnable
    result = run_historical(source, data)
    assert result.var_series["x"] == [4.0, 11.0, 11.0, 4.0]
    assert result.var_series["y"] == result.var_series["x"]


def test_collected_label_set_x_preserves_other_label_coordinates():
    source = '//@version=4\nstudy("label x")\nvar item = label.new(0, 100)\nlabel.set_x(item, bar_index)\n'
    assert analyze_coverage(source).is_runnable
    label = run_historical(source, _candles()).final_state["main::item"]
    assert label.x == 3 and label.y == 100


def test_previous_label_delete_ignores_first_bar_na_only():
    source = '//@version=4\nstudy("previous label")\nitem = label.new(bar_index, close)\nlabel.delete(item[1])\n'
    result = run_historical(source, _candles())
    assert [label.deleted for label in result.var_series["item"]] == [True, True, True, False]

"""math.sum의 이동 합계·초기 이력·지원 경계를 독립 수기로 확인한다."""

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def _run(body: str, closes: list[float] | None = None):
    values = closes or [1.0, 2.0, 3.0, 4.0]
    frame = pd.DataFrame(
        {
            "open": [1.0] * len(values),
            "high": [2.0] * len(values),
            "low": [0.5] * len(values),
            "close": values,
            "volume": [1.0] * len(values),
        }
    )
    return run_historical('//@version=5\nindicator("sum")\n' + body, frame)


def test_math_sum_ignores_na_and_warms_up() -> None:
    result = _run("x = math.sum(close, 3)\n", [1.0, math.nan, 2.0, 3.0, 4.0])
    values = result.var_series["x"]
    assert all(math.isnan(v) for v in values[:3])
    assert values[3:] == [6.0, 9.0]


def test_math_sum_keyword_order_and_independent_callsites() -> None:
    result = _run("x = math.sum(length=2, source=close)\ny = math.sum(open, length=2)\n")
    assert math.isnan(result.var_series["x"][0])
    assert result.var_series["x"][1:] == [3.0, 5.0, 7.0]
    assert math.isnan(result.var_series["y"][0])
    assert result.var_series["y"][1:] == [2.0, 2.0, 2.0]


def test_math_sum_series_length_uses_all_preceding_valid_values() -> None:
    result = _run("x = math.sum(close, bar_index < 2 ? 2 : 3)\n")
    assert math.isnan(result.var_series["x"][0])
    assert result.var_series["x"][1:] == [3.0, 6.0, 9.0]


def test_math_sum_integer_source_returns_float() -> None:
    values = _run("x = math.sum(1, 2)\n").var_series["x"]
    assert math.isnan(values[0])
    assert values[1:] == [2.0, 2.0, 2.0]
    assert all(type(value) is float for value in values)


@pytest.mark.parametrize("length", ["2.5", "true", "0", "-1", "na", "1e309"])
def test_math_sum_rejects_invalid_length(length: str) -> None:
    with pytest.raises(PineRuntimeError, match="positive int"):
        _run(f"x = math.sum(close, {length})\n")


def test_math_sum_coverage_rejects_wrong_arity_only() -> None:
    assert not analyze_coverage("x = math.sum(close)").is_runnable
    assert analyze_coverage("x = math.sum(close, math.max(2, 3))").is_runnable


def test_math_sum_repeated_call_in_same_bar_fails_closed() -> None:
    with pytest.raises(PineRuntimeError, match="repeated in one bar"):
        _run("for i = 0 to 1\n    x = math.sum(close, 2)\n")


def test_math_sum_sparse_calls_are_explicitly_unsupported() -> None:
    with pytest.raises(PineRuntimeError, match="nonconsecutive"):
        _run("x = bar_index % 2 == 0 ? math.sum(close, 2) : 0\n")


@pytest.mark.parametrize("source", ['"bad"', "true", "array.new_float(1)", "1e309"])
def test_math_sum_rejects_unverified_source_types(source: str) -> None:
    with pytest.raises(PineRuntimeError, match="finite numeric"):
        _run(f"x = math.sum({source}, 2)\n")


@pytest.mark.parametrize(
    "arguments",
    [
        "close",
        "close, 2, 3",
        "close, source=open, length=2",
        "length=2, close",
        "source=close, length=2, length=3",
    ],
)
def test_math_sum_rejects_missing_excess_and_duplicate_arguments(arguments: str) -> None:
    with pytest.raises(PineRuntimeError, match=r"math\.sum"):
        _run(f"x = math.sum({arguments})\n")


def test_math_sum_nonfinite_result_is_outside_supported_numeric_domain() -> None:
    with pytest.raises(PineRuntimeError, match="finite"):
        _run("x = math.sum(1e308, 2)\n")


def test_math_sum_evaluates_source_side_effect_only_once() -> None:
    result = _run(
        "var values = array.new_float(0)\n"
        "array.push(values, 1)\n"
        "array.push(values, 2)\n"
        "x = math.sum(array.pop(values), 1)\n"
        "remaining = array.size(values)\n"
    )
    assert result.var_series["x"] == [2.0] * 4
    assert result.var_series["remaining"] == [1, 2, 3, 4]

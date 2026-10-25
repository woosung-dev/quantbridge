"""기본 high/low overload와 구버전 표시·입력 상수의 제한된 계약."""

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError
from src.strategy.pine_v2.rendering import PineColor, color_named
from src.strategy.pine_v2.stdlib import StdlibDispatcher


def frame():
    return pd.DataFrame(
        {
            "open": [10, 11, 9, 13],
            "high": [12, 14, 11, 16],
            "low": [8, 7, 6, 10],
            "close": [10, 11, 9, 13],
            "volume": 1,
        }
    )


def normalized(values):
    return [None if isinstance(v, float) and math.isnan(v) else v for v in values]


@pytest.mark.parametrize("version,prefix", [(3, ""), (5, "ta.")])
def test_implicit_high_low_preserves_explicit_sources_and_length_warmup(version, prefix):
    header = 'study("Bounds")' if version < 5 else 'indicator("Bounds")'
    source = f"""//@version={version}
{header}
h = {prefix}highest(2)
l = {prefix}lowest(3)
explicitHigh = {prefix}highest(high, 2)
explicitLow = {prefix}lowest(low, 3)
closeHigh = {prefix}highest(close, 2)
"""
    out = run_historical(source, frame())
    assert not out.errors
    assert normalized(out.var_series["h"]) == [None, 14, 14, 16]
    assert normalized(out.var_series["l"]) == [None, None, 6, 6]
    assert normalized(out.var_series["h"]) == normalized(out.var_series["explicitHigh"])
    assert normalized(out.var_series["l"]) == normalized(out.var_series["explicitLow"])
    assert normalized(out.var_series["closeHigh"]) == [None, 11, 11, 13]


@pytest.mark.parametrize(
    "function,source_key,values,expected",
    [
        ("ta.highest", "high", [2, 9, 3], [None, 9, 9]),
        ("ta.lowest", "low", [8, 1, 7], [None, 1, 1]),
    ],
)
def test_default_source_callsite_and_udf_prefix_are_independent(
    function, source_key, values, expected
):
    dispatcher = StdlibDispatcher()
    results = []
    for value in values:
        dispatcher.push_call_prefix("left")
        results.append(dispatcher.call(function, 9, [2], **{source_key: value}))
        dispatcher.pop_call_prefix()
        dispatcher.push_call_prefix("right")
        dispatcher.call(function, 9, [2], **{source_key: value * 100})
        dispatcher.pop_call_prefix()
        dispatcher.call(function, 10, [2], **{source_key: value * 1000})
    assert normalized(results) == expected


@pytest.mark.parametrize("function", ["ta.highest", "ta.lowest"])
@pytest.mark.parametrize("args", [[], [1, 2, 3]])
def test_missing_or_excess_arguments_are_not_silently_accepted(function, args):
    with pytest.raises(TypeError):
        StdlibDispatcher().call(function, 1, args, high=10, low=1)


@pytest.mark.parametrize("length", [0, -1, float("nan"), float("inf")])
def test_invalid_length_keeps_existing_nan_contract(length):
    for function in ["ta.highest", "ta.lowest"]:
        assert math.isnan(StdlibDispatcher().call(function, 1, [length], high=10, low=1))


@pytest.mark.parametrize("version", [1, 2, 3])
def test_official_legacy_display_colors_are_available_only_as_existing_nop(version):
    colors = [
        "black",
        "silver",
        "gray",
        "white",
        "maroon",
        "red",
        "purple",
        "fuchsia",
        "green",
        "lime",
        "olive",
        "yellow",
        "navy",
        "blue",
        "teal",
        "aqua",
        "orange",
    ]
    source = f'//@version={version}\nstudy("Colors")\n'
    source += "\n".join(
        f"c{i} = {name}\nplot(close, color={name})" for i, name in enumerate(colors)
    )
    out = run_historical(source, frame())
    assert not out.errors
    for i, name in enumerate(colors):
        assert all(
            isinstance(value, PineColor) and value == color_named(name, version)
            for value in out.var_series[f"c{i}"]
        )


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize("name", ["white", "fuchsia"])
def test_bare_legacy_colors_remain_undefined_in_modern_versions(version, name):
    with pytest.raises(PineRuntimeError, match=f"Undefined name: {name}"):
        run_historical(
            f'//@version={version}\nindicator("Colors")\nplot(close, color={name})\n', frame()
        )


def test_user_global_and_local_names_precede_legacy_color_fallback():
    source = """//@version=3
study("User names")
white = 7
fuchsia = 4
f(white) => white + 2
answer = f(3) + white + fuchsia
"""
    out = run_historical(source, frame())
    assert out.var_series["answer"] == [16] * 4


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize(
    "form", ['0.5, "Multiplier", float', 'defval=0.5, title="Multiplier", type=float']
)
def test_legacy_float_input_type_is_a_constant_not_a_cast(version, form):
    out = run_historical(
        f'//@version={version}\nstudy("Input")\nmultiplier = input({form})\n', frame()
    )
    assert out.var_series["multiplier"] == [0.5] * 4


@pytest.mark.parametrize("version", [4, 5])
def test_bare_float_input_constant_not_enabled_for_modern_versions(version):
    with pytest.raises(PineRuntimeError, match="Undefined name: float"):
        run_historical(
            f'//@version={version}\nindicator("Input")\nx = input(0.5, type=float)\n', frame()
        )


def test_float_cast_does_not_become_supported_by_name_constant():
    with pytest.raises(PineRuntimeError, match="not supported"):
        run_historical('//@version=3\nstudy("Cast")\nx = float(1)\n', frame())

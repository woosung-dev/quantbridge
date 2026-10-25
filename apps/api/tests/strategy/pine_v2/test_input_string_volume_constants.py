"""공식 v4 입력 상수와 표시 형식만 지원하며 숫자 문자열 포맷은 추정하지 않는다."""

import pandas as pd
import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def frame():
    return pd.DataFrame(
        {key: [5183.0, 5500.0] for key in ("open", "high", "low", "close", "volume")}
    )


def test_v4_string_type_keeps_default_and_explicit_override():
    source = """//@version=4
study("String", format=format.volume)
kind = input("EMA", title="Kind", type=input.string, options=["EMA", "SMA"])
selected = kind == "EMA"
"""
    assert analyze_coverage(source).is_runnable
    assert run_historical(source, frame()).var_series["selected"] == [True, True]
    assert run_historical(source, frame(), input_overrides={"kind": "SMA"}).var_series[
        "selected"
    ] == [
        False,
        False,
    ]


@pytest.mark.parametrize("call", ["tostring", "str.tostring"])
def test_volume_text_format_is_rejected_instead_of_ignoring_its_market_logic(call):
    source = f'//@version=4\nstudy("Format")\nx = {call}(close, format.volume)\n'
    with pytest.raises(PineRuntimeError, match=r"format\.volume formatting is not supported"):
        run_historical(source, frame())


@pytest.mark.parametrize("name", ["format.unobserved", "input.unobserved"])
def test_constants_do_not_enable_unlisted_namespace_attributes(name):
    assert not analyze_coverage(f'//@version=4\nstudy("Unknown")\nx = {name}\n').is_runnable

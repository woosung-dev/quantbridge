"""v4/v5 native 3값 관측과 v6 bool 2값 계약을 구분한다.

2026-10-20 native stage: EMA3/5 워밍업에서 cross·비교·eq는 NA,
`and`는 false, `not eq`는 true. slow가 처음 유효한 봉의 cross는 false다.
기존 테스트는 v6 문서의 bool 2값 계약을 v5에도 적용해 잘못된 기대값을 잠갔다.
공식 버전 경계: https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/#boolean-values-cannot-be-na
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.event_loop import run_historical


def ohlcv(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes, "volume": 1.0}
    )


def _run(body: str, version: int, closes: list[float] | None = None):
    declaration = 'study("NA contract")' if version < 5 else 'indicator("NA contract")'
    if version < 5:
        body = body.replace("ta.", "")
    result = run_historical(
        f"//@version={version}\n{declaration}\n{body}\n",
        ohlcv(closes if closes is not None else [10.0, 20.0, 30.0, 40.0, 50.0]),
    )
    assert not result.errors, result.errors
    return result.var_series


def _three_state(value) -> int:
    return -1 if isinstance(value, float) and math.isnan(value) else int(bool(value))


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize("operator", ["<", "<=", ">", ">=", "==", "!="])
def test_na_comparison_preserves_version_contract(version, operator):
    values = _run(f"x = close[10] {operator} close", version)["x"]
    assert [_three_state(value) for value in values] == ([-1] * 5 if version < 6 else [0] * 5)


@pytest.mark.parametrize("version", [4, 5, 6])
def test_na_boolean_history_keeps_legacy_unknown_until_both_sides_exist(version):
    values = _run("b = ta.ema(close, 3) > ta.ema(close, 5)\nx = b != b[1]", version)
    assert [_three_state(value) for value in values["b"]] == (
        [-1, -1, -1, -1, 1] if version < 6 else [0, 0, 0, 0, 1]
    )
    assert [_three_state(value) for value in values["x"]] == (
        [-1] * 5 if version < 6 else [0, 0, 0, 0, 1]
    )


@pytest.mark.parametrize("version", [4, 5])
def test_native_stage_keeps_cross_compare_and_not_boundaries(version):
    # 실제 native v4 source는 상수10, v5는10/20/30/40/50이다. 나눗셈 차이는
    # 여기서 고치지 않고 관측된 source를 직접 공급해 NA 단계만 분리한다.
    closes = [10.0] * 5 if version == 4 else [10.0, 20.0, 30.0, 40.0, 50.0]
    values = _run(
        "fast = ta.ema(close, 3)\nslow = ta.ema(close, 5)\n"
        "up = ta.crossover(fast, slow)\ndown = ta.crossunder(fast, slow)\n"
        "price_cmp = slow < close\nstrong = price_cmp and up\n"
        "eq = up == strong\nfinal = not eq",
        version,
        closes,
    )
    expected = {
        "up": [-1, -1, -1, -1, 0],
        "down": [-1, -1, -1, -1, 0],
        "price_cmp": [-1, -1, -1, -1, int(version == 5)],
        "strong": [0, 0, 0, 0, 0],
        "eq": [-1, -1, -1, -1, 1],
        "final": [1, 1, 1, 1, 0],
    }
    for name, wanted in expected.items():
        assert [_three_state(value) for value in values[name]] == wanted, name


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize("function", ["crossover", "crossunder", "cross"])
def test_cross_current_na_is_distinct_from_missing_previous_sample(version, function):
    values = _run(
        f"a = bar_index == 2 ? na : close\nx = ta.{function}(a, 25)",
        version,
        [10.0, 30.0, 20.0, 10.0, 30.0],
    )["x"]
    # 첫 표본/NA 직후에는 전봉 교차 증거가 없으므로 false. 현재 NA만 3값이다.
    expected = [
        0,
        int(function in ("crossover", "cross")),
        -1 if version < 6 else 0,
        0,
        int(function in ("crossover", "cross")),
    ]
    assert [_three_state(value) for value in values] == expected


@pytest.mark.parametrize("version", [4, 5, 6])
def test_not_na_and_explicit_na_checks_remain_concrete(version):
    values = _run("x = not (close[10] > 0)\ny = na(close[10])\nz = not na(close)", version)
    assert all(value is True for name in ("x", "y", "z") for value in values[name])


@pytest.mark.parametrize("version", [4, 5, 6])
def test_na_arithmetic_and_control_flow_do_not_create_an_entry(version):
    source = (
        f'//@version={version}\nstrategy("NA condition")\n'
        'if close[10] + 1 > 0\n    strategy.entry("L", strategy.long)\n'
    )
    outcome = run_backtest_v2(source, ohlcv([10.0] * 5), BacktestConfig())
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None and not outcome.result.trades
    values = _run("x = close[10] + 1", version)["x"]
    assert all(math.isnan(value) for value in values)


@pytest.mark.parametrize("version", [4, 5])
@pytest.mark.parametrize(
    "expression,expected",
    [
        ("q and true", False),
        ("q and false", False),
        ("q and q", False),
        ("q or true", True),
        ("q or false", False),
        ("q or q", False),
    ],
)
def test_native_logic_consumes_unknown_as_false(version, expression, expected):
    # native cross가 반환한 NA를 직접 공급해 cross 수리 여부와 독립 검증한다.
    values = _run(f"q = close[10]\nx = {expression}", version)["x"]
    assert all(value is expected for value in values)

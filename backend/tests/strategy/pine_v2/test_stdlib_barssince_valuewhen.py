"""Sprint 8c — ta.barssince / ta.valuewhen stdlib 추가."""
from __future__ import annotations

import math as _math

import pandas as pd
from pynescript import ast as pyne_ast

from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1.0] * len(closes),
    })


def _run_script(source: str, closes: list[float]) -> list[Interpreter]:
    interp = Interpreter(BarContext(_ohlcv(closes)), PersistentStore())
    snapshots: list[Interpreter] = []
    tree = pyne_ast.parse(source)
    while interp.bar.advance():
        interp.store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        interp.store.commit_bar()
        interp.append_var_series()
        snapshots.append(interp)
    return snapshots


def test_barssince_counts_bars_since_true() -> None:
    # close > 10 이 bar0(close=11)에서 true. 이후 bar1=5,bar2=7,bar3=15.
    # 기대: barssince(close>10) = [0, 1, 2, 0]
    src = "cnt = ta.barssince(close > 10)\n"
    snaps = _run_script(src, [11.0, 5.0, 7.0, 15.0])
    series = list(snaps[-1]._var_series["cnt"])
    assert series == [0, 1, 2, 0]


def test_barssince_nan_before_first_true() -> None:
    src = "cnt = ta.barssince(close > 100)\n"
    snaps = _run_script(src, [5.0, 10.0, 20.0])
    series = snaps[-1]._var_series["cnt"]
    assert all(_math.isnan(v) for v in series)


def test_valuewhen_occurrence_zero_returns_latest_match() -> None:
    # cond = close > 10: bar0=F, bar1=T(15), bar2=F, bar3=T(20), bar4=F
    # valuewhen(cond, close, 0) = 가장 최근 true일 때 close
    # = [nan, 15, 15, 20, 20]
    src = """
c = close > 10
v = ta.valuewhen(c, close, 0)
"""
    snaps = _run_script(src, [5.0, 15.0, 8.0, 20.0, 9.0])
    series = list(snaps[-1]._var_series["v"])
    assert _math.isnan(series[0])
    assert series[1:] == [15.0, 15.0, 20.0, 20.0]


def test_valuewhen_occurrence_one_returns_previous_match() -> None:
    # occurrence=1 → 직전 true
    src = """
c = close > 10
v = ta.valuewhen(c, close, 1)
"""
    snaps = _run_script(src, [5.0, 15.0, 8.0, 20.0, 9.0])
    series = snaps[-1]._var_series["v"]
    assert _math.isnan(series[0])
    assert _math.isnan(series[1])
    assert _math.isnan(series[2])
    assert series[3] == 15.0
    assert series[4] == 15.0


# ---------------------------------------------------------------------------
# Task 8 — tostring / request.security NOP / v4 alias barssince/valuewhen
# ---------------------------------------------------------------------------


def test_v4_alias_barssince_routes_to_ta() -> None:
    # v4 스크립트처럼 prefix 없이 barssince(...) 호출 가능해야
    src = "cnt = barssince(close > 10)\n"
    snaps = _run_script(src, [11.0, 5.0])
    assert list(snaps[-1]._var_series["cnt"]) == [0, 1]


def test_v4_alias_valuewhen_routes_to_ta() -> None:
    src = """
c = close > 10
v = valuewhen(c, close, 0)
"""
    snaps = _run_script(src, [11.0, 5.0])
    assert snaps[-1]._var_series["v"][0] == 11.0


def test_tostring_numeric_returns_string() -> None:
    src = "s = tostring(3.14)\n"
    snaps = _run_script(src, [10.0])
    assert list(snaps[-1]._var_series["s"]) == ["3.14"]


def test_request_security_is_nop_returns_expression_arg() -> None:
    # request.security(symbol, tf, expression) → Sprint 8c stub: expression arg 값
    src = "v = request.security(syminfo.tickerid, '1D', close)\n"
    snaps = _run_script(src, [10.0, 20.0])
    assert list(snaps[-1]._var_series["v"]) == [10.0, 20.0]

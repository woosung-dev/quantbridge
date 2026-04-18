"""Sprint 8c — ta.barssince / ta.valuewhen stdlib 추가."""
from __future__ import annotations

import math as _math

import pandas as pd
import pytest
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
    series = snaps[-1]._var_series["cnt"]
    assert series == [0, 1, 2, 0]


def test_barssince_nan_before_first_true() -> None:
    src = "cnt = ta.barssince(close > 100)\n"
    snaps = _run_script(src, [5.0, 10.0, 20.0])
    series = snaps[-1]._var_series["cnt"]
    assert all(_math.isnan(v) for v in series)

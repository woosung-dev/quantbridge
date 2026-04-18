"""Sprint 8c — user-defined function (`=>`) 단위 테스트."""
from __future__ import annotations

import math
import pandas as pd
import pytest
from pynescript import ast as pyne_ast

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, PineRuntimeError
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1.0] * len(closes),
    })


def _interp(closes: list[float]) -> Interpreter:
    bar = BarContext(_ohlcv(closes))
    return Interpreter(bar, PersistentStore())


def test_function_def_registers_in_user_functions() -> None:
    interp = _interp([10.0, 11.0])
    tree = pyne_ast.parse("foo(x) => x + 1\n")
    interp.bar.advance()
    interp.execute(tree)
    assert "foo" in interp._user_functions
    fn = interp._user_functions["foo"]
    assert isinstance(fn, pyne_ast.FunctionDef)
    assert [p.name for p in fn.args] == ["x"]

"""Sprint 8c — multi-return tuple unpacking 단위 테스트."""
from __future__ import annotations

import pandas as pd
import pytest
from pynescript import ast as pyne_ast

from src.strategy.pine_v2.interpreter import BarContext, Interpreter, PineRuntimeError
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1.0] * len(closes),
    })


def _run_one_bar(source: str, closes: list[float]) -> Interpreter:
    interp = Interpreter(BarContext(_ohlcv(closes)), PersistentStore())
    interp.bar.advance()
    interp.execute(pyne_ast.parse(source))
    return interp


def test_user_function_returns_tuple_literal() -> None:
    src = """foo(x) =>
    [x, x * 2]
[a, b] = foo(5)
"""
    interp = _run_one_bar(src, [10.0])
    assert interp._transient["a"] == 5
    assert interp._transient["b"] == 10


def test_tuple_unpack_three_elements() -> None:
    src = """trio(x) =>
    [x, x + 1, x + 2]
[p, q, r] = trio(10)
"""
    interp = _run_one_bar(src, [10.0])
    assert (
        interp._transient["p"],
        interp._transient["q"],
        interp._transient["r"],
    ) == (10, 11, 12)


def test_tuple_unpack_arity_mismatch_raises() -> None:
    src = """pair(x) =>
    [x, x * 2]
[a, b, c] = pair(5)
"""
    with pytest.raises(PineRuntimeError, match="tuple unpack.*expected.*got"):
        _run_one_bar(src, [10.0])

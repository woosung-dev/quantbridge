"""Interpreter 표현식 평가 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine.interpreter import Environment, evaluate_expression
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse_expression


def _env_with_ohlcv() -> Environment:
    close = pd.Series([10.0, 11.0, 12.0, 11.5, 10.8], name="close")
    high = close + 0.5
    low = close - 0.5
    open_ = close - 0.1
    volume = pd.Series([100.0] * 5)
    return Environment.with_ohlcv(
        open_=open_, high=high, low=low, close=close, volume=volume,
    )


def _eval(src: str, env: Environment | None = None):
    env = env or _env_with_ohlcv()
    expr = parse_expression(tokenize(src))
    return evaluate_expression(expr, env)


def test_eval_int_literal():
    assert _eval("42") == 42


def test_eval_float_literal():
    assert _eval("3.14") == 3.14


def test_eval_boolean_literals():
    assert _eval("true") is True
    assert _eval("false") is False


def test_eval_string_literal():
    assert _eval('"hello"') == "hello"


def test_eval_close_identifier_returns_series():
    result = _eval("close")
    assert isinstance(result, pd.Series)
    assert len(result) == 5


def test_eval_arithmetic_with_series():
    # close + 1 → Series broadcast
    result = _eval("close + 1")
    expected = pd.Series([11.0, 12.0, 13.0, 12.5, 11.8])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_arithmetic_scalar():
    assert _eval("2 + 3 * 4") == 14
    assert _eval("(2 + 3) * 4") == 20


def test_eval_comparison_returns_bool_series():
    result = _eval("close > 11")
    expected = pd.Series([False, False, True, True, False])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_logical_and_series():
    result = _eval("close > 10 and close < 12")
    expected = pd.Series([False, True, False, True, True])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_history_reference_shift():
    # close[1] → close.shift(1)
    result = _eval("close[1]")
    expected = pd.Series([np.nan, 10.0, 11.0, 12.0, 11.5])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_ternary_series():
    # close > 11 ? close : 0
    result = _eval("close > 11 ? close : 0")
    expected = pd.Series([0.0, 0.0, 12.0, 11.5, 0.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_fncall_ta_sma():
    result = _eval("ta.sma(close, 3)")
    close = _env_with_ohlcv().lookup("close")
    expected = close.rolling(3).mean()
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_not_operator():
    result = _eval("not (close > 11)")
    expected = pd.Series([True, True, False, False, True])
    pd.testing.assert_series_equal(result, expected, check_names=False)

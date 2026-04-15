"""Interpreter 문 실행 + 시그널 수집 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine.interpreter import execute_program
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse


def _ohlcv(n: int = 10) -> dict[str, pd.Series]:
    close = pd.Series(np.linspace(10.0, 20.0, n))
    return {
        "open_": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": pd.Series([100.0] * n),
    }


def test_var_decl_then_reference():
    src = """x = close
y = x + 1
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    pd.testing.assert_series_equal(
        result.metadata["vars"]["y"],
        result.metadata["vars"]["x"] + 1,
        check_names=False,
    )


def test_strategy_entry_sets_entries_series():
    src = """buy = close > 15
if buy
    strategy.entry("Long", strategy.long)
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    # close=[10..20] 10개 중 > 15인 지점에서 True
    assert result.entries.any()
    # index >= 5에서 True (linspace(10,20,10) 기준)
    assert bool(result.entries.iloc[-1]) is True
    assert bool(result.entries.iloc[0]) is False


def test_strategy_close_sets_exits_series():
    src = """sell = close > 18
if sell
    strategy.close("Long")
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert result.exits.any()


def test_strategy_exit_with_bracket_order_populates_brackets():
    # stop/limit 인자가 있으면 스프린트 2에서 bracket 필드를 채움
    src = """x = close
strategy.exit("tp", "Long", stop=x, limit=x)
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    # stop/limit 둘 다 있으면 sl_stop, tp_limit Series가 채워짐
    assert result.sl_stop is not None
    assert result.tp_limit is not None


def test_assign_walrus_updates_binding():
    # 스프린트 1: :=는 scalar/series 치환으로 단순 처리 (bar-by-bar 루프 없음)
    src = """x = 0
x := close
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert isinstance(result.metadata["vars"]["x"], pd.Series)


def test_if_stmt_without_signal_call_is_noop():
    src = """if close > 15
    y = close
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    # entries/exits는 모두 False (signal 호출 없음)
    assert not result.entries.any()
    assert not result.exits.any()

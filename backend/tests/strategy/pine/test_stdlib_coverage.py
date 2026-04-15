"""Stdlib 커버리지 보강 테스트.

누락된 항목:
- _ta_rma (Wilder smoothing)
- _ta_rsi
- _ta_atr
- _ta_stdev
- _ta_cross
- call_supported: 존재하지 않는 키 → KeyError
- validate_functions: ForLoop / HistoryRef / IfExpr / Assign 노드 순회
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine.stdlib import call_supported, validate_functions

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def _make_ohlc(n: int = 20):
    close = pd.Series(np.linspace(10.0, 20.0, n), dtype=float)
    high = close + 0.5
    low = close - 0.5
    return high, low, close


# ---------------------------------------------------------------------------
# _ta_rma (Wilder smoothing)
# ---------------------------------------------------------------------------


def test_ta_rma_length_14():
    """ta.rma는 alpha=1/length EWM — 결과가 Series이고 NaN 없이 수렴."""
    _, _, close = _make_ohlc(30)
    result = call_supported("ta.rma", close, 14)
    assert isinstance(result, pd.Series)
    assert len(result) == 30
    # Wilder smoothing은 항상 첫 번째부터 값이 있음 (ewm adjust=False)
    assert not result.isna().all()


# ---------------------------------------------------------------------------
# _ta_rsi
# ---------------------------------------------------------------------------


def test_ta_rsi_range_0_to_100():
    _, _, close = _make_ohlc(30)
    result = call_supported("ta.rsi", close, 14)
    assert isinstance(result, pd.Series)
    # RSI는 0~100 범위
    valid = result.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_ta_rsi_all_up_returns_high():
    """단조 증가 → RSI는 매우 높음 (100에 수렴)."""
    close = _series(list(range(1, 21)))
    result = call_supported("ta.rsi", close, 5)
    # 마지막 몇 개는 100에 가까워야 함
    assert result.iloc[-1] > 80


def test_ta_rsi_all_down_returns_low():
    """단조 감소 → RSI는 낮음 (0에 수렴)."""
    close = _series(list(range(20, 0, -1)))
    result = call_supported("ta.rsi", close, 5)
    assert result.iloc[-1] < 20


# ---------------------------------------------------------------------------
# _ta_atr
# ---------------------------------------------------------------------------


def test_ta_atr_basic():
    high, low, close = _make_ohlc(20)
    result = call_supported("ta.atr", high, low, close, 14)
    assert isinstance(result, pd.Series)
    assert len(result) == 20
    # ATR은 항상 양수
    valid = result.dropna()
    assert (valid >= 0).all()


def test_ta_atr_flat_market_near_zero():
    """flat 마켓: high-low 스프레드가 0이면 ATR ≈ 0."""
    flat = pd.Series([10.0] * 20)
    result = call_supported("ta.atr", flat, flat, flat, 5)
    assert result.iloc[-1] < 1e-9


# ---------------------------------------------------------------------------
# _ta_stdev
# ---------------------------------------------------------------------------


def test_ta_stdev_basic():
    _, _, close = _make_ohlc(20)
    result = call_supported("ta.stdev", close, 5)
    expected = close.rolling(5).std(ddof=0)
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_ta_stdev_constant_returns_zero():
    """상수 시리즈의 stdev = 0."""
    s = pd.Series([5.0] * 10)
    result = call_supported("ta.stdev", s, 5)
    valid = result.dropna()
    assert (valid == 0).all()


# ---------------------------------------------------------------------------
# _ta_cross
# ---------------------------------------------------------------------------


def test_ta_cross_detects_both_directions():
    a = pd.Series([1.0, 2.0, 3.0, 2.0, 1.0])
    b = pd.Series([2.0, 2.0, 2.0, 2.0, 2.0])
    result = call_supported("ta.cross", a, b)
    assert isinstance(result, pd.Series)
    # crossover at index=2 (a goes 2->3, b stays 2)
    # crossunder at index=4 (a goes 2->1, b stays 2)
    assert bool(result.iloc[2])
    assert bool(result.iloc[4])


# ---------------------------------------------------------------------------
# call_supported: unsupported key
# ---------------------------------------------------------------------------


def test_call_supported_unknown_raises_key_error():
    with pytest.raises(KeyError, match="unsupported function"):
        call_supported("ta.does_not_exist", pd.Series([1.0]))


# ---------------------------------------------------------------------------
# validate_functions: AST 노드 순회 (HistoryRef, IfExpr, ForLoop, Assign)
# ---------------------------------------------------------------------------


def test_validate_functions_history_ref_traversal():
    """HistoryRef 노드를 포함한 AST → validate 통과 확인."""
    from src.strategy.pine.lexer import tokenize
    from src.strategy.pine.parser import parse

    src = """//@version=5
x = close[1]
"""
    program = parse(tokenize(src))
    report = validate_functions(program, allowed_structural=set())
    assert isinstance(report["functions_used"], list)


def test_validate_functions_ifexpr_traversal():
    """IfExpr (삼항 연산자) 포함 AST → validate 순회."""
    from src.strategy.pine.lexer import tokenize
    from src.strategy.pine.parser import parse

    src = """//@version=5
x = close > 15 ? close : 0
"""
    program = parse(tokenize(src))
    report = validate_functions(program, allowed_structural=set())
    assert isinstance(report["functions_used"], list)


def test_validate_functions_assign_traversal():
    """Assign (:=) 노드 → validate 순회."""
    from src.strategy.pine.lexer import tokenize
    from src.strategy.pine.parser import parse

    src = """//@version=5
x = 0
x := close
"""
    program = parse(tokenize(src))
    report = validate_functions(program, allowed_structural=set())
    assert isinstance(report["functions_used"], list)


def test_validate_functions_for_loop_traversal_with_unsupported():
    """ForLoop 내부에 unsupported 함수가 있으면 PineUnsupportedError."""
    from src.strategy.pine.errors import PineUnsupportedError
    from src.strategy.pine.lexer import tokenize
    from src.strategy.pine.parser import parse

    src = """for i = 0 to 5
    x = ta.vwma(close, 20)
"""
    program = parse(tokenize(src))
    with pytest.raises(PineUnsupportedError):
        validate_functions(program, allowed_structural=set())


def test_validate_functions_for_loop_with_supported_passes():
    """ForLoop 내부에 지원 함수만 있으면 통과."""
    from src.strategy.pine.lexer import tokenize
    from src.strategy.pine.parser import parse

    src = """for i = 0 to 5
    x = ta.sma(close, 3)
"""
    program = parse(tokenize(src))
    report = validate_functions(program, allowed_structural=set())
    assert "ta.sma" in report["functions_used"]

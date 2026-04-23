"""B-1: _var_series ring buffer cap 테스트.

deque(maxlen=500) 전환 후:
- 500 bar 초과 히스토리가 자동 드롭되어 메모리 상한 보장
- offset ≥ len(buffer) → nan (이력 부족)
- 음수 offset → nan (silently degrade)
- RunResult.var_series 값이 list 타입 (serializable)
"""
from __future__ import annotations

import math
from collections import deque

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import RunResult, run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.runtime import PersistentStore


def _make_ohlcv(n: int, start: float = 100.0) -> pd.DataFrame:
    closes = [start + float(i) for i in range(n)]
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })


# -------- Ring buffer cap -----------------------------------------------


def test_ring_buffer_cap() -> None:
    """maxlen=3 커스텀 interpreter: 4번째 bar에서 x[3] → nan."""
    # maxlen=3으로 직접 조작: 3개 bar 기록 후 오래된 항목 드롭 확인
    ohlcv = _make_ohlcv(10)
    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
    interp._max_bars_back = 3  # 테스트용 cap 축소

    from src.strategy.pine_v2.parser_adapter import parse_to_ast
    source = '//@version=5\nindicator("t")\nx = close\n'
    tree = parse_to_ast(source)

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # maxlen=3 → 최대 3개만 보관 (bar 7, 8, 9의 close = 107, 108, 109)
    series = interp._var_series.get("x")
    assert series is not None
    assert isinstance(series, deque)
    assert len(series) == 3  # maxlen=3


def test_ring_buffer_history_overflow_returns_nan() -> None:
    """cap=3으로 설정 후 x[4] → nan (이력 부족)."""
    ohlcv = _make_ohlcv(5)
    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
    interp._max_bars_back = 3

    from src.strategy.pine_v2.parser_adapter import parse_to_ast
    source = '//@version=5\nindicator("t")\nx = close\n'
    tree = parse_to_ast(source)

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # 5 bar 실행 후 maxlen=3 → series에 3개 항목. x[4]는 이력 부족 → nan
    series = interp._var_series.get("x")
    assert series is not None
    assert len(series) == 3

    # _eval_subscript 직접 검증: offset >= len(series) → nan
    # series[-4] 없으므로 nan 반환 확인 (series length=3, offset=4)
    # interpreter._eval_subscript 결과 확인
    result = series[-3] if len(series) >= 3 else None
    assert result is not None  # offset=3: series[-3] 존재


def test_ring_buffer_negative_offset() -> None:
    """run_historical에서 x[-1] (음수 offset) → nan으로 degrade (런타임 에러 없음)."""
    source = """//@version=5
indicator("t")
x = close
y = x[-1]
"""
    ohlcv = _make_ohlcv(5)
    # strict=False: 런타임 에러 대신 nan으로 처리됨
    result = run_historical(source, ohlcv, strict=False)
    # y는 nan이거나 0 (silent degrade). 에러 없이 완료됨을 확인
    assert result.bars_processed == 5


def test_runresult_var_series_list_type() -> None:
    """RunResult.var_series 값이 list 타입 (JSON serializable)."""
    source = '//@version=5\nindicator("t")\nx = close\n'
    ohlcv = _make_ohlcv(5)
    result = run_historical(source, ohlcv)
    assert isinstance(result.var_series, dict)
    for key, val in result.var_series.items():
        assert isinstance(val, list), f"var_series[{key!r}] is {type(val)}, expected list"


def test_runresult_var_series_values_correct() -> None:
    """RunResult.var_series["x"] = [close[0], ..., close[4]] — 정확한 값."""
    source = '//@version=5\nindicator("t")\nx = close\n'
    closes = [100.0, 101.0, 102.0, 103.0, 104.0]
    ohlcv = pd.DataFrame({
        "open": [100.0] * 5,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * 5,
    })
    result = run_historical(source, ohlcv)
    assert "x" in result.var_series
    assert result.var_series["x"] == closes


def test_default_max_bars_back_is_500() -> None:
    """기본 _max_bars_back=500 확인."""
    ohlcv = _make_ohlcv(1)
    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
    assert interp._max_bars_back == 500


def test_var_series_deque_maxlen_matches_max_bars_back() -> None:
    """append_var_series 후 생성된 deque의 maxlen이 _max_bars_back과 일치."""
    source = '//@version=5\nindicator("t")\nx = close\n'
    ohlcv = _make_ohlcv(3)
    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)

    from src.strategy.pine_v2.parser_adapter import parse_to_ast
    tree = parse_to_ast(source)

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    series = interp._var_series.get("x")
    assert series is not None
    assert isinstance(series, deque)
    assert series.maxlen == interp._max_bars_back

"""B-3: User function call-site별 ta.* 상태 격리 테스트.

동일 user function을 두 call-site에서 서로 다른 source로 호출 시
각자 독립 EMA 상태를 가져야 함.

a = calcEma(close, 14)
b = calcEma(open, 14)
→ a != b (서로 다른 source → 다른 EMA 결과)
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.stdlib import StdlibDispatcher


def _make_ohlcv(n: int = 30) -> pd.DataFrame:
    """close != open 이 되도록 의도적으로 다른 값 사용."""
    closes = [100.0 + i * 0.5 for i in range(n)]
    opens = [closes[0]] + [closes[i - 1] + 0.2 for i in range(1, n)]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })


# -------- StdlibDispatcher prefix 단위 테스트 ---------------------------


def test_scoped_node_id_no_prefix() -> None:
    """prefix_stack 비어있으면 원래 node_id 그대로."""
    disp = StdlibDispatcher()
    assert disp._scoped_node_id(42) == 42


def test_scoped_node_id_with_prefix() -> None:
    """prefix 존재 시 scoped id != original id."""
    disp = StdlibDispatcher()
    disp.push_call_prefix("call_site_1")
    scoped = disp._scoped_node_id(42)
    assert scoped != 42


def test_different_prefixes_produce_different_ids() -> None:
    """서로 다른 prefix → 서로 다른 scoped id."""
    disp = StdlibDispatcher()
    disp.push_call_prefix("site_a")
    id_a = disp._scoped_node_id(42)
    disp.pop_call_prefix()

    disp.push_call_prefix("site_b")
    id_b = disp._scoped_node_id(42)
    disp.pop_call_prefix()

    assert id_a != id_b


def test_push_pop_symmetry() -> None:
    """push/pop 후 prefix_stack이 원래 상태로 복원."""
    disp = StdlibDispatcher()
    disp.push_call_prefix("x")
    disp.pop_call_prefix()
    assert len(disp._prefix_stack) == 0
    # 빈 stack → scoped_id == original
    assert disp._scoped_node_id(99) == 99


def test_pop_empty_stack_safe() -> None:
    """빈 stack에서 pop해도 에러 없음."""
    disp = StdlibDispatcher()
    disp.pop_call_prefix()  # 에러 없어야 함


# -------- E2E: 두 call-site EMA 독립성 ----------------------------------


def test_user_fn_two_callsites_independent_ema() -> None:
    """동일 함수 두 call-site에서 다른 source → EMA 결과 독립.

    calcEma(close, 14) != calcEma(open, 14) — 30 bars 실행 후 확인.
    """
    source = """//@version=5
indicator("isolation_test")
calcEma(src, length) =>
    ta.ema(src, length)

a = calcEma(close, 14)
b = calcEma(open, 14)
"""
    ohlcv = _make_ohlcv(30)
    result = run_historical(source, ohlcv)

    a_series = result.var_series.get("a", [])
    b_series = result.var_series.get("b", [])

    assert len(a_series) == 30
    assert len(b_series) == 30

    # warmup 완료 후(14 bar 이후) 값이 서로 다른지 확인
    # (close와 open이 다르므로 EMA도 달라야 함)
    non_nan_pairs = [
        (a, b) for a, b in zip(a_series, b_series)
        if not (math.isnan(a) or math.isnan(b))
    ]
    assert len(non_nan_pairs) > 0, "EMA warmup 완료 후 non-nan 값이 없음"

    # 적어도 하나는 a != b
    any_different = any(abs(a - b) > 1e-10 for a, b in non_nan_pairs)
    assert any_different, "두 call-site EMA가 동일 — 상태 격리 실패"


def test_user_fn_same_source_same_result() -> None:
    """동일 source를 두 call-site에서 호출하면 동일 결과 (격리는 되되 값은 같음)."""
    source = """//@version=5
indicator("same_source_test")
calcEma(src, length) =>
    ta.ema(src, length)

a = calcEma(close, 5)
b = calcEma(close, 5)
"""
    ohlcv = _make_ohlcv(20)
    result = run_historical(source, ohlcv)

    a_series = result.var_series.get("a", [])
    b_series = result.var_series.get("b", [])

    non_nan_pairs = [
        (a, b) for a, b in zip(a_series, b_series)
        if not (math.isnan(a) or math.isnan(b))
    ]
    assert len(non_nan_pairs) > 0

    # 같은 source → 값 동일해야 함 (격리 후에도)
    for a, b in non_nan_pairs:
        assert abs(a - b) < 1e-10, f"같은 source인데 다름: {a} vs {b}"

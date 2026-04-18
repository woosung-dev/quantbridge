"""Pine AST interpreter 단위 테스트 (Week 2 Day 1-2).

합성 Pine 스크립트 + 5~10 bar 시뮬레이션으로 다음 의미론 검증:
- 표현식: 산술/비교/논리/ternary/history 구독
- 문장: 일반 assign / var / varip / re-assign / if-else
- built-in series (close/open/high/low/volume) + bar_index + na / true / false
- 선언/렌더링 호출은 NOP으로 처리되어 오류 없이 통과
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import RunResult, run_historical
from src.strategy.pine_v2.interpreter import (
    BarContext,
    Interpreter,
    PineRuntimeError,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def _make_ohlcv(closes: list[float]) -> pd.DataFrame:
    """close 기준 OHLCV — open=prev_close, high=close*1.01, low=close*0.99, volume=100."""
    n = len(closes)
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })


# -------- 표현식 평가 (단일 bar) --------------------------------------


def test_arithmetic_add_sub_mul_div() -> None:
    source = '//@version=5\nindicator("t")\na = 1 + 2 * 3 - 4 / 2\n'
    result = run_historical(source, _make_ohlcv([10.0]))
    # 1 + 6 - 2 = 5.0
    assert result.final_state == {"a": 5.0}


def test_comparison_operators() -> None:
    source = '//@version=5\nindicator("t")\ngt = 10 > 5\nlt = 3 < 1\neq = 5 == 5\nneq = 5 != 6\n'
    result = run_historical(source, _make_ohlcv([10.0]))
    assert result.final_state == {"gt": True, "lt": False, "eq": True, "neq": True}


def test_bool_short_circuit_and_or() -> None:
    # and 단축: 첫 falsy 반환; or 단축: 첫 truthy 반환
    source = """//@version=5
indicator("t")
a = true and 42
b = false and 42
c = false or 99
d = true or 99
"""
    result = run_historical(source, _make_ohlcv([10.0]))
    assert result.final_state == {"a": 42, "b": False, "c": 99, "d": True}


def test_unary_not_and_neg() -> None:
    source = """//@version=5
indicator("t")
a = not true
b = not false
c = -5
"""
    result = run_historical(source, _make_ohlcv([10.0]))
    assert result.final_state == {"a": False, "b": True, "c": -5}


def test_ternary_conditional() -> None:
    source = """//@version=5
indicator("t")
x = 10
a = x > 5 ? 100 : 200
b = x < 5 ? 100 : 200
"""
    result = run_historical(source, _make_ohlcv([10.0]))
    assert result.final_state["a"] == 100
    assert result.final_state["b"] == 200


def test_builtin_close_open_high_low_volume() -> None:
    source = """//@version=5
indicator("t")
c = close
o = open
h = high
l = low
v = volume
"""
    result = run_historical(source, _make_ohlcv([100.0]))
    state = result.final_state
    assert state["c"] == 100.0
    # open = closes[0] 기본. 단일 bar라 close와 동일.
    assert state["o"] == 100.0
    assert state["h"] == 101.0  # close * 1.01
    assert state["l"] == 99.0
    assert state["v"] == 100.0


def test_bar_index_increments_each_bar() -> None:
    source = '//@version=5\nindicator("t")\nidx = bar_index\n'
    result = run_historical(source, _make_ohlcv([1.0, 2.0, 3.0]))
    # state_history[i] 는 i번째 bar commit 후 — bar_index == i
    assert result.state_history[0]["idx"] == 0
    assert result.state_history[1]["idx"] == 1
    assert result.state_history[2]["idx"] == 2


# -------- 문장 실행 + var/varip 통합 -----------------------------------


def test_var_counter_persists_across_bars() -> None:
    """Pine var 의미론: `var counter = 0` + `counter := counter + 1` → 1,2,3."""
    source = """//@version=5
indicator("t")
var counter = 0
counter := counter + 1
"""
    result = run_historical(source, _make_ohlcv([1.0, 2.0, 3.0]))
    history = [s["main::counter"] for s in result.state_history]
    assert history == [1, 2, 3]


def test_var_highest_close() -> None:
    """var를 활용한 rolling max close (Pine 일반 패턴)."""
    source = """//@version=5
indicator("t")
var highest = 0.0
if close > highest
    highest := close
"""
    closes = [10.0, 15.0, 12.0, 20.0, 18.0]
    result = run_historical(source, _make_ohlcv(closes))
    history = [s["main::highest"] for s in result.state_history]
    assert history == [10.0, 15.0, 15.0, 20.0, 20.0]


def test_varip_declared_via_interpreter_keeps_flag() -> None:
    source = """//@version=5
indicator("t")
varip rt = 100
"""
    result = run_historical(source, _make_ohlcv([1.0, 2.0]))
    # Historical에서 varip도 var처럼 bar 간 유지; flag만 확인
    assert result.final_state["main::rt"] == 100
    # PersistentStore internal 확인은 별도 유닛 — 여기선 값 유지만


def test_transient_variable_resets_each_bar() -> None:
    """`x = close + 1` (var 없음) — 매 bar 재평가. 매 bar 시작 시 리셋되며 직후 재평가됨.

    final_state는 마지막 bar 실행 직후 transient 스냅샷이므로 마지막 bar의 값.
    state_history는 각 bar 직후 — 매 bar 다른 값이어야 transient 리셋 검증.
    """
    source = """//@version=5
indicator("t")
x = close + 1
"""
    closes = [10.0, 20.0, 30.0]
    result = run_historical(source, _make_ohlcv(closes))
    # 마지막 bar의 값
    assert result.final_state == {"x": 31.0}
    # 각 bar마다 재평가 증거 — transient가 누적되지 않음
    history_x = [s["x"] for s in result.state_history]
    assert history_x == [11.0, 21.0, 31.0]


def test_if_else_branches() -> None:
    source = """//@version=5
indicator("t")
var count_up = 0
var count_down = 0
if close > open
    count_up := count_up + 1
else
    count_down := count_down + 1
"""
    # 3 up + 2 down 시나리오
    closes = [10.0, 15.0, 12.0, 20.0, 18.0]  # close > open (bar 0은 open=close로 == )
    result = run_historical(source, _make_ohlcv(closes))
    # bar 0: open=close=10 → close > open은 False → down
    # bar 1: open=10, close=15 → up
    # bar 2: open=15, close=12 → down
    # bar 3: open=12, close=20 → up
    # bar 4: open=20, close=18 → down
    assert result.final_state["main::count_up"] == 2
    assert result.final_state["main::count_down"] == 3


def test_history_subscript_close_n_bars_ago() -> None:
    """`close[1]`은 1 bar 전 close; bar 0에선 na."""
    source = """//@version=5
indicator("t")
var prev_close_history = 0.0
prev_close_history := close[1]
"""
    closes = [10.0, 20.0, 30.0]
    result = run_historical(source, _make_ohlcv(closes))
    hist = [s["main::prev_close_history"] for s in result.state_history]
    # bar 0: close[1] = na(nan) → 0.0 기본값이 nan으로 덮임
    assert math.isnan(hist[0])
    assert hist[1] == 10.0
    assert hist[2] == 20.0


def test_na_propagation_in_arithmetic() -> None:
    """na는 산술에서 전파되어 결과도 na."""
    source = """//@version=5
indicator("t")
var y = 0.0
y := close[5] + 1.0
"""
    result = run_historical(source, _make_ohlcv([10.0]))  # 1 bar만 — close[5]는 na
    assert math.isnan(result.final_state["main::y"])


# -------- NOP 호출 관용 처리 -------------------------------------------


def test_declaration_and_plot_and_alert_are_nop() -> None:
    """indicator(), plot(), alert() 같은 선언/렌더링 호출은 조용히 통과."""
    source = """//@version=5
indicator("MyIndicator", overlay=true)
plot(close)
bgcolor(color=na)
alert("test")
a = 42
"""
    result = run_historical(source, _make_ohlcv([10.0]))
    assert result.final_state == {"a": 42}


def test_input_call_returns_defval() -> None:
    """input.int(14, 'Length')는 defval(14)를 돌려줘서 수식에 사용 가능해야 함."""
    source = """//@version=5
indicator("t")
length = input.int(14, "Length")
result = length * 2
"""
    r = run_historical(source, _make_ohlcv([10.0]))
    assert r.final_state == {"length": 14, "result": 28}


# -------- 에러 경로 ---------------------------------------------------


def test_undefined_name_raises_pine_runtime_error() -> None:
    source = '//@version=5\nindicator("t")\nx = undefined_var + 1\n'
    with pytest.raises(PineRuntimeError, match="Undefined name"):
        run_historical(source, _make_ohlcv([10.0]))


def test_unsupported_call_raises() -> None:
    """Day 1-2 범위 밖인 stdlib Call은 stdlib 연결 전까지 에러."""
    source = '//@version=5\nindicator("t")\nx = ta.sma(close, 14)\n'
    with pytest.raises(PineRuntimeError, match="not supported"):
        run_historical(source, _make_ohlcv([10.0]))


def test_strict_false_collects_errors() -> None:
    source = '//@version=5\nindicator("t")\nx = ta.sma(close, 14)\n'
    result = run_historical(source, _make_ohlcv([10.0, 11.0]), strict=False)
    assert len(result.errors) == 2  # 각 bar마다 오류
    assert all("not supported" in msg for _, msg in result.errors)


# -------- 낮은 수준 직접 사용 (Interpreter class) ----------------------


def test_interpreter_class_level_usage() -> None:
    """Event loop 없이 직접 Interpreter 구성."""
    ohlcv = _make_ohlcv([100.0])
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)

    bar.advance()
    store.begin_bar()
    tree = parse_to_ast('//@version=5\nindicator("t")\nz = close * 2\n')
    interp.execute(tree)
    store.commit_bar()

    assert interp._transient["z"] == 200.0


def test_run_result_repr() -> None:
    result = run_historical(
        '//@version=5\nindicator("t")\nvar k = 0\nk := k+1\n',
        _make_ohlcv([1.0, 2.0, 3.0]),
    )
    assert isinstance(result, RunResult)
    assert len(result) == 3
    assert result.bars_processed == 3
    d = result.to_dict()
    assert d["bars_processed"] == 3
    assert d["state_history_length"] == 3

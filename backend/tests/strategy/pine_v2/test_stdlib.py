"""ta.* stdlib + user 변수 series subscript 회귀 테스트 (Week 2 Day 3)."""
from __future__ import annotations

import math

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.stdlib import (
    IndicatorState,
    ta_crossover,
    ta_crossunder,
    ta_ema,
    ta_rsi,
    ta_sma,
)


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * len(closes),
    })


# -------- 단위 테스트: 지표 함수 직접 ----------------------------------


def test_ta_sma_warmup_returns_nan_until_length() -> None:
    state = IndicatorState()
    nid = 1
    vals = [ta_sma(state, nid, v, 3) for v in [1.0, 2.0, 3.0, 4.0]]
    assert math.isnan(vals[0])
    assert math.isnan(vals[1])
    assert vals[2] == 2.0  # (1+2+3)/3
    assert vals[3] == 3.0  # (2+3+4)/3


def test_ta_ema_seed_matches_sma_then_decays() -> None:
    state = IndicatorState()
    nid = 1
    vals = [ta_ema(state, nid, v, 3) for v in [1.0, 2.0, 3.0, 10.0]]
    # 첫 3 bar 후 seed = SMA(1,2,3) = 2.0
    assert math.isnan(vals[0])
    assert math.isnan(vals[1])
    assert vals[2] == 2.0
    # bar 4: alpha = 2/(3+1) = 0.5; ema = 0.5*10 + 0.5*2 = 6.0
    assert vals[3] == 6.0


def test_ta_crossover_detects_upward_cross() -> None:
    state = IndicatorState()
    nid = 1
    # a가 b보다 작다가 커지는 패턴
    pairs = [(5, 10), (6, 10), (11, 10), (12, 10)]
    results = [ta_crossover(state, nid, a, b) for a, b in pairs]
    assert results == [False, False, True, False]  # bar 2에서 crossover


def test_ta_crossunder_detects_downward_cross() -> None:
    state = IndicatorState()
    nid = 1
    pairs = [(15, 10), (14, 10), (9, 10), (8, 10)]
    results = [ta_crossunder(state, nid, a, b) for a, b in pairs]
    assert results == [False, False, True, False]


def test_ta_rsi_approaches_100_on_monotone_gains() -> None:
    state = IndicatorState()
    nid = 1
    vals = [ta_rsi(state, nid, v, 3) for v in [10, 11, 12, 13, 14, 15, 16]]
    # 연속 상승 → loss = 0 → RSI = 100
    assert vals[-1] == 100.0


# -------- 통합 테스트: interpreter + event_loop 를 통한 Pine 구문 ------


def test_ta_sma_via_pine_source() -> None:
    source = """//@version=5
indicator("t")
fast = ta.sma(close, 3)
"""
    result = run_historical(source, _ohlcv([1.0, 2.0, 3.0, 4.0]))
    history = [s.get("fast") for s in result.state_history]
    assert math.isnan(history[0])
    assert math.isnan(history[1])
    assert history[2] == 2.0
    assert history[3] == 3.0


def test_ta_crossover_via_pine_source() -> None:
    source = """//@version=5
indicator("t")
fast = ta.sma(close, 2)
slow = ta.sma(close, 4)
cross = ta.crossover(fast, slow)
"""
    # 하락하다가 상승: fast가 slow를 아래에서 위로 돌파
    closes = [20.0, 19.0, 18.0, 17.0, 16.0, 17.0, 19.0, 22.0, 26.0]
    result = run_historical(source, _ohlcv(closes))
    crosses = [s.get("cross") for s in result.state_history]
    # 실측한 crossover 이벤트가 최소 1회 발생
    assert any(c is True for c in crosses), f"crossover 미발생. hist={crosses}"


def test_na_function_call() -> None:
    source = """//@version=5
indicator("t")
var x = 0.0
x := close[10]
check = na(x)
"""
    result = run_historical(source, _ohlcv([10.0, 11.0, 12.0]))  # 3 bars only
    # close[10]은 항상 na (3 bar밖에 없으므로)
    assert all(s.get("check") is True for s in result.state_history)


def test_nz_function_replaces_na() -> None:
    source = """//@version=5
indicator("t")
result = nz(close[100], 99.0)
"""
    r = run_historical(source, _ohlcv([10.0]))
    assert r.final_state["result"] == 99.0


def test_ta_atr_uses_prev_close() -> None:
    source = """//@version=5
indicator("t")
atr = ta.atr(3)
"""
    # high/low/close 생성 — atr는 high-low + gap 등
    closes = [10.0, 11.0, 12.0, 11.5, 13.0]
    r = run_historical(source, _ohlcv(closes))
    atrs = [s.get("atr") for s in r.state_history]
    # 첫 두 bar는 warmup (length=3)
    assert math.isnan(atrs[0])
    assert math.isnan(atrs[1])
    # 3번째부터 값 존재
    assert not math.isnan(atrs[2])


# -------- user 변수 series subscript ----------------------------------


def test_user_var_subscript_returns_previous_bar_value() -> None:
    """var hprice = 0.0 \n hprice := close \n prev = hprice[1] — 직전 bar의 close."""
    source = """//@version=5
indicator("t")
var hprice = 0.0
hprice := close
prev = hprice[1]
"""
    closes = [100.0, 110.0, 120.0, 130.0]
    r = run_historical(source, _ohlcv(closes))
    prevs = [s.get("prev") for s in r.state_history]
    # bar 0: prev = nan (hprice는 이번 bar만 갱신)
    assert math.isnan(prevs[0])
    # bar 1: prev = hprice[1] = bar 0의 hprice = 100
    assert prevs[1] == 100.0
    # bar 2: prev = bar 1의 hprice = 110
    assert prevs[2] == 110.0


def test_user_var_subscript_on_transient_variable() -> None:
    """transient 변수도 series 로 기록됨."""
    source = """//@version=5
indicator("t")
x = close + 1
prev = x[1]
"""
    closes = [10.0, 20.0, 30.0]
    r = run_historical(source, _ohlcv(closes))
    prevs = [s.get("prev") for s in r.state_history]
    assert math.isnan(prevs[0])
    assert prevs[1] == 11.0
    assert prevs[2] == 21.0


def test_self_referential_reassign_uses_prev_bar() -> None:
    """Pine 일반 패턴: x := cond ? new_value : x[1]."""
    source = """//@version=5
indicator("t")
var signal = 0.0
signal := close > open ? close : signal[1]
"""
    # 번갈아 up/down
    closes = [10.0, 15.0, 12.0, 20.0]
    r = run_historical(source, _ohlcv(closes))
    hist = [s["main::signal"] for s in r.state_history]
    # bar 0: close > open? open=10, close=10 → False. signal[1]은 na. 초기값 0.0 유지됨? na?
    # self-referential이고 첫 bar는 signal[1]이 없음 → na. fallback 0.0 (declare_if_new 초기값)
    # 실제 결과 — hist[0]을 확인
    assert hist[0] in (0.0,) or math.isnan(hist[0])  # nan or 0.0 허용
    # bar 1: close=15 > open=10 → True → signal := close = 15
    assert hist[1] == 15.0
    # bar 2: close=12 > open=15 → False → signal[1] = 15
    assert hist[2] == 15.0
    # bar 3: close=20 > open=12 → True → 20
    assert hist[3] == 20.0


# -------- Sprint 8b: Pine v4 legacy alias + iff --------------------------


def test_v4_stdlib_alias_atr_ema_crossover() -> None:
    """Pine v4 prefix 없는 atr/ema/crossover가 ta.* 로 재라우팅."""
    source = (
        "//@version=4\n"
        "study('t', overlay=true)\n"
        "x = atr(5)\n"
        "y = ema(close, 3)\n"
        "crossed = crossover(close, ema(close, 2))\n"
    )
    ohlcv = _ohlcv([101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
    result = run_historical(source, ohlcv)
    assert result.bars_processed == 6
    # 마지막 bar의 x(atr)가 float 값 산출
    final_x = result.final_state.get("x")
    assert isinstance(final_x, float)


def test_v4_iff_ternary_equivalent() -> None:
    """iff(cond, then, else) = cond ? then : else."""
    source = (
        "//@version=4\n"
        "study('t')\n"
        "z = iff(close > open, 1.0, 0.0)\n"
    )
    # bar 0: close==open → 0.0, bar 1: close>open → 1.0
    ohlcv = pd.DataFrame(
        {
            "open": [100.0, 100.0],
            "high": [101.0, 111.0],
            "low": [99.0, 99.0],
            "close": [100.0, 110.0],
            "volume": [100.0, 100.0],
        }
    )
    result = run_historical(source, ohlcv)
    assert result.final_state.get("z") == 1.0


def test_v4_nz_with_two_args() -> None:
    """nz(value, default) — value가 na면 default."""
    source = (
        "//@version=4\n"
        "study('t')\n"
        "x = close\n"
        "y = nz(x[1], 42.0)\n"
    )
    ohlcv = _ohlcv([100.0, 110.0])
    result = run_historical(source, ohlcv)
    # bar 0에서 x[1]은 na → y=42.0, bar 1에서 x[1]=100 → y=100
    assert result.state_history[0]["y"] == 42.0
    assert result.state_history[1]["y"] == 100.0

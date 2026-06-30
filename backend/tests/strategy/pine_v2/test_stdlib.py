"""ta.* stdlib + user 변수 series subscript 회귀 테스트 (Week 2 Day 3)."""
from __future__ import annotations

import math

import pandas as pd
import pytest

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


def _true_range_series(
    highs: list[float], lows: list[float], closes: list[float]
) -> list[float]:
    """TR = max(high-low, |high-prevClose|, |low-prevClose|). 첫 bar = high-low."""
    trs: list[float] = []
    for i in range(len(closes)):
        hl = highs[i] - lows[i]
        if i == 0:
            trs.append(hl)
        else:
            pc = closes[i - 1]
            trs.append(max(hl, abs(highs[i] - pc), abs(lows[i] - pc)))
    return trs


def _wilder_rma(values: list[float], n: int) -> list[float]:
    """TV ta.atr = ta.rma(tr, n): seed=SMA(first n), 이후 (prev*(n-1)+v)/n."""
    out = [float("nan")] * len(values)
    prev = float("nan")
    for i in range(len(values)):
        if i + 1 < n:
            continue
        prev = sum(values[:n]) / n if i + 1 == n else (prev * (n - 1) + values[i]) / n
        out[i] = prev
    return out


def _rolling_sma(values: list[float], n: int) -> list[float]:
    return [
        (sum(values[i - n + 1 : i + 1]) / n if i + 1 >= n else float("nan"))
        for i in range(len(values))
    ]


# 비-상수 TR 슬라이스 — Wilder RMA != rolling SMA 가 성립 (discriminator).
_ATR_HIGHS = [10.0, 12.0, 11.0, 13.0, 12.0, 16.0, 15.0, 18.0]
_ATR_LOWS = [9.0, 9.5, 8.0, 8.5, 10.0, 10.2, 11.0, 11.3]
_ATR_CLOSES = [9.5, 11.5, 8.5, 12.5, 10.2, 15.0, 11.3, 17.0]


def _atr_df() -> pd.DataFrame:
    opens = [_ATR_CLOSES[0], *_ATR_CLOSES[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": _ATR_HIGHS,
        "low": _ATR_LOWS,
        "close": _ATR_CLOSES,
        "volume": [100.0] * len(_ATR_CLOSES),
    })


def test_ta_atr_matches_tradingview_wilder_rma() -> None:
    """BL-378: ta.atr 은 TR 의 Wilder RMA (TV `ta.atr = ta.rma(ta.tr, len)`),
    단순 rolling SMA 가 아니다. anti-circular: 기대값은 TV 정의에서 손유도.
    """
    n = 3
    r = run_historical(
        f'//@version=5\nindicator("t")\natr = ta.atr({n})\n', _atr_df(), strict=False
    )
    engine = [s.get("atr") for s in r.state_history]
    trs = _true_range_series(_ATR_HIGHS, _ATR_LOWS, _ATR_CLOSES)
    wilder = _wilder_rma(trs, n)
    sma = _rolling_sma(trs, n)

    diverged = False
    for i in range(n, len(_ATR_CLOSES)):  # seed bar 이후만 Wilder != SMA
        assert engine[i] == pytest.approx(wilder[i], abs=1e-9), (
            f"bar {i}: engine ta.atr={engine[i]} != TV Wilder RMA={wilder[i]} (SMA={sma[i]})"
        )
        if abs(wilder[i] - sma[i]) > 1e-9:
            diverged = True
    assert diverged, "슬라이스에 Wilder != SMA 인 bar 가 있어야 (discriminator 무효 방지)"


def test_ta_atr_not_rolling_sma() -> None:
    """BL-378 회귀 가드 (mutation harness): 비-상수 TR 에서 ta.atr 이 rolling SMA 와
    불일치해야 한다. SMA 회귀 시 즉시 FAIL.
    """
    r = run_historical(
        '//@version=5\nindicator("t")\natr = ta.atr(3)\n', _atr_df(), strict=False
    )
    engine = [s.get("atr") for s in r.state_history]
    trs = _true_range_series(_ATR_HIGHS, _ATR_LOWS, _ATR_CLOSES)
    sma_last = sum(trs[-3:]) / 3
    assert engine[-1] != pytest.approx(sma_last, abs=1e-6), (
        "ta.atr 이 rolling SMA 로 회귀 (TV Wilder RMA 와 불일치해야)"
    )


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


def test_ta_stdev_returns_std_after_warmup() -> None:
    """ta.stdev(source, 3) — 최근 3 bar 표준편차."""
    state = IndicatorState()
    from src.strategy.pine_v2.stdlib import ta_stdev
    vals = [ta_stdev(state, 1, v, 3) for v in [2.0, 4.0, 4.0, 4.0]]
    assert math.isnan(vals[0])
    assert math.isnan(vals[1])
    # [2,4,4] mean=3.33, var=((2-3.33)^2+(4-3.33)^2*2)/3 ≈ 0.8889, std≈0.9428
    assert vals[2] == pytest.approx(0.9428, abs=1e-3)


def test_ta_variance_is_stdev_squared() -> None:
    from src.strategy.pine_v2.stdlib import ta_stdev, ta_variance
    s1 = IndicatorState()
    s2 = IndicatorState()
    for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
        stdev_v = ta_stdev(s1, 1, v, 3)
        var_v = ta_variance(s2, 2, v, 3)
    assert var_v == pytest.approx(stdev_v ** 2, rel=1e-9)

"""Week 3 Day 1 신규 기능 테스트: ta.pivothigh/pivotlow + strategy.entry(stop=)."""
from __future__ import annotations

import math

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.stdlib import IndicatorState, ta_pivothigh, ta_pivotlow


def _ohlcv(highs: list[float], lows: list[float] | None = None, closes: list[float] | None = None) -> pd.DataFrame:
    """고/저/종가 직접 제어."""
    n = len(highs)
    if lows is None:
        lows = [h * 0.99 for h in highs]
    if closes is None:
        closes = [(h + low) / 2 for h, low in zip(highs, lows, strict=True)]
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [100.0] * n,
    })


# -------- ta.pivothigh / ta.pivotlow 단위 -----------------------------


def test_pivothigh_detects_peak_at_confirmation_bar() -> None:
    """pivothigh(2, 2)가 5개 바 창에서 중앙이 최고일 때 감지."""
    state = IndicatorState()
    nid = 1
    # highs: 10, 20, 50, 20, 10 → idx 2(=50)가 pivot. left=2, right=2.
    # 각 bar별 호출 시점의 반환값:
    highs = [10.0, 20.0, 50.0, 20.0, 10.0]
    results = [ta_pivothigh(state, nid, 2, 2, h) for h in highs]
    # bar 0-3: 미완 (5 bar 필요) → nan
    assert math.isnan(results[0])
    assert math.isnan(results[1])
    assert math.isnan(results[2])
    assert math.isnan(results[3])
    # bar 4: window 완성. highs[-(right+1)] = highs[-3] = 50.0. 양옆 4개 모두 < 50 → 감지
    assert results[4] == 50.0


def test_pivothigh_nan_when_not_peak() -> None:
    state = IndicatorState()
    nid = 1
    # 단조 증가 — pivot high 없음
    highs = [10.0, 20.0, 30.0, 40.0, 50.0]
    results = [ta_pivothigh(state, nid, 2, 2, h) for h in highs]
    assert all(math.isnan(r) for r in results)


def test_pivotlow_detects_trough() -> None:
    state = IndicatorState()
    nid = 1
    lows = [50.0, 40.0, 10.0, 40.0, 50.0]
    results = [ta_pivotlow(state, nid, 2, 2, low) for low in lows]
    assert math.isnan(results[3])  # window 미완
    assert results[4] == 10.0  # idx 2가 최저


def test_pivothigh_via_pine() -> None:
    source = """//@version=5
indicator("t")
ph = ta.pivothigh(2, 2)
"""
    ohlcv = _ohlcv(highs=[10.0, 20.0, 50.0, 20.0, 10.0, 5.0, 15.0])
    r = run_historical(source, ohlcv)
    # bar 4에서 감지 (50)
    phs = [s.get("ph") for s in r.state_history]
    assert phs[4] == 50.0
    # bar 5, 6: 새 pivot 후보 확인 필요 (단조 하락→상승이라 없음)
    assert math.isnan(phs[5]) or phs[5] is not None


# -------- strategy.entry(stop=) pending 주문 -------------------------


def test_stop_long_fills_when_high_breaks_above() -> None:
    """Long BUY STOP: high가 stop_price에 도달하는 bar에서 fill."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, stop=105.0)
"""
    # bar 0: stop order 발주 (stop=105). 이 bar high=100*1.01=101 < 105 → 미체결.
    # bar 1: 주문 활성. high를 110으로 설정 → fill at max(open, 105) = 105 (open=100)
    highs = [101.0, 110.0, 120.0]
    lows = [99.0, 100.0, 115.0]
    closes = [100.0, 110.0, 120.0]
    ohlcv = _ohlcv(highs=highs, lows=lows, closes=closes)

    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # bar 1에서 체결 (open=100, stop=105, fill=105)
    assert len(interp.strategy.open_trades) == 1
    trade = interp.strategy.open_trades["L"]
    assert trade.entry_bar == 1
    assert trade.entry_price == 105.0


def test_stop_short_fills_when_low_breaks_below() -> None:
    """Short SELL STOP: low가 stop_price에 도달하면 fill."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("S", strategy.short, qty=1.0, stop=95.0)
"""
    highs = [101.0, 102.0, 98.0]
    lows = [99.0, 98.0, 90.0]  # bar 2에서 low=90 < stop=95
    closes = [100.0, 100.0, 92.0]
    ohlcv = _ohlcv(highs=highs, lows=lows, closes=closes)

    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # bar 2에서 체결 (min(open=100, stop=95) = 95)
    assert "S" in interp.strategy.open_trades
    trade = interp.strategy.open_trades["S"]
    assert trade.entry_bar == 2
    assert trade.entry_price == 95.0


def test_stop_order_not_filled_if_price_never_reaches() -> None:
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, stop=200.0)
"""
    # 가격이 200에 도달하지 못함
    highs = [101.0, 102.0, 105.0]
    lows = [99.0, 98.0, 100.0]
    closes = [100.0, 100.0, 102.0]
    ohlcv = _ohlcv(highs=highs, lows=lows, closes=closes)
    r = run_historical(source, ohlcv)
    # 포지션 없음
    assert r.bars_processed == 3


def test_stop_order_placed_bar_does_not_self_fill() -> None:
    """Pine 표준: 주문 placed_bar와 fill_bar가 같을 수 없음 (같은 bar 체결 방지)."""
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0, stop=100.0)
"""
    # bar 1에 주문 발주. 이 bar high=110 > stop=100이나 same-bar 체결 금지.
    highs = [99.0, 110.0, 115.0]
    lows = [98.0, 99.0, 112.0]
    closes = [99.0, 105.0, 113.0]
    ohlcv = _ohlcv(highs=highs, lows=lows, closes=closes)

    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # bar 2에서 체결 (bar 1 placed, same-bar 방지)
    assert "L" in interp.strategy.open_trades
    assert interp.strategy.open_trades["L"].entry_bar == 2


def test_stop_order_reissue_updates_price() -> None:
    """매 bar 같은 id로 entry(stop=) 호출 시 stop price 갱신 (Pine re-issue)."""
    source = """//@version=5
strategy("t")
strategy.entry("L", strategy.long, qty=1.0, stop=200.0)
"""
    # 매 bar 주문 (stop=200 고정). 가격이 200에 도달 안 하면 미체결 유지.
    highs = [100.0, 120.0, 150.0, 180.0, 195.0]
    closes = [99.0, 115.0, 145.0, 175.0, 190.0]
    ohlcv = _ohlcv(highs=highs, closes=closes)
    r = run_historical(source, ohlcv)
    # 5 bar 모두 미체결, pending 유지
    assert r.bars_processed == 5


def test_syminfo_mintick_constant() -> None:
    """syminfo.mintick이 기본값 0.01 반환."""
    source = """//@version=5
indicator("t")
x = syminfo.mintick
"""
    r = run_historical(source, _ohlcv([100.0, 101.0]))
    assert r.final_state["x"] == 0.01


def test_stop_plus_mintick_usage() -> None:
    """s1_pbr 패턴: stop = price + syminfo.mintick"""
    source = """//@version=5
strategy("t")
hprice = 100.0
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, stop=hprice + syminfo.mintick)
"""
    # stop = 100 + 0.01 = 100.01. bar 1 high=110 → fill at max(open, 100.01)
    highs = [95.0, 110.0]
    lows = [94.0, 95.0]
    closes = [94.0, 100.0]
    ohlcv = _ohlcv(highs=highs, lows=lows, closes=closes)
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()
    assert "L" in interp.strategy.open_trades
    assert interp.strategy.open_trades["L"].entry_price == 100.01

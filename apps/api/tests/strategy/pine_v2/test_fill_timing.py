# fill_timing 옵션 hand-oracle — bar_close(기본, 기존 동작) vs next_bar_open(TV 정합)
"""시장가 체결 타이밍 옵션 (TV parity):

- bar_close (기본): 신호 bar 종가 즉시 체결 — 기존 동작 byte-identical.
- next_bar_open: 시장가 entry/close/close_all 을 인텐트 큐에 넣고 다음 bar
  시가에 체결 (TV `process_orders_on_close=false` 기본과 동일).
- 마지막 bar 신호는 체결 기회가 없어 미체결 (TV 동일).
- stop= pending entry / strategy.exit 브래킷은 기존 트리거 경로 그대로.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical

SOURCE = """//@version=5
strategy("t")
if bar_index == 2
    strategy.entry("L", strategy.long, qty=1)
if bar_index == 4
    strategy.close("L")
"""

_OPENS = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
_CLOSES = [105.0, 115.0, 125.0, 135.0, 145.0, 155.0]


def _ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    return pd.DataFrame(
        {
            "open": _OPENS,
            "high": [c + 1.0 for c in _CLOSES],
            "low": [o - 1.0 for o in _OPENS],
            "close": _CLOSES,
            "volume": [100.0] * 6,
        },
        index=idx,
    )


def test_default_bar_close_unchanged() -> None:
    """기본(bar_close) = 기존 동작: bar2 종가 진입 / bar4 종가 청산."""
    r = run_historical(SOURCE, _ohlcv(), strict=True)
    state = r.strategy_state
    assert state is not None
    assert len(state.closed_trades) == 1
    t = state.closed_trades[0]
    assert t.entry_bar == 2
    assert t.entry_price == pytest.approx(125.0)  # close[2]
    assert t.exit_bar == 4
    assert t.exit_price == pytest.approx(145.0)  # close[4]


def test_next_bar_open_entry_and_close() -> None:
    """next_bar_open: bar2 신호 → bar3 시가 진입, bar4 close 신호 → bar5 시가 청산."""
    r = run_historical(SOURCE, _ohlcv(), strict=True, fill_timing="next_bar_open")
    state = r.strategy_state
    assert state is not None
    assert len(state.closed_trades) == 1
    t = state.closed_trades[0]
    assert t.entry_bar == 3
    assert t.entry_price == pytest.approx(130.0)  # open[3]
    assert t.exit_bar == 5
    assert t.exit_price == pytest.approx(150.0)  # open[5]


def test_next_bar_open_last_bar_signal_never_fills() -> None:
    """마지막 bar 신호 = 다음 bar 없음 → 미체결 (TV 동일)."""
    source = """//@version=5
strategy("t")
if bar_index == 5
    strategy.entry("L", strategy.long, qty=1)
"""
    r = run_historical(source, _ohlcv(), strict=True, fill_timing="next_bar_open")
    state = r.strategy_state
    assert state is not None
    assert len(state.closed_trades) == 0
    assert len(state.open_trades) == 0


def test_next_bar_open_default_sizing_uses_fill_open() -> None:
    """qty 미지정 + percent_of_equity → 체결 시가(open) 기준 sizing (TV 정합)."""
    source = """//@version=5
strategy("t")
if bar_index == 2
    strategy.entry("L", strategy.long)
"""
    r = run_historical(
        source,
        _ohlcv(),
        strict=True,
        initial_capital=1300.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100.0,
        fill_timing="next_bar_open",
    )
    state = r.strategy_state
    assert state is not None
    assert len(state.open_trades) == 1
    t = next(iter(state.open_trades.values()))
    assert t.entry_bar == 3
    assert t.entry_price == pytest.approx(130.0)
    assert t.qty == pytest.approx(1300.0 / 130.0)  # equity 100% / open[3] = 10


def test_next_bar_open_close_all() -> None:
    """close_all 인텐트도 다음 bar 시가 체결."""
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1)
if bar_index == 3
    strategy.close_all()
"""
    r = run_historical(source, _ohlcv(), strict=True, fill_timing="next_bar_open")
    state = r.strategy_state
    assert state is not None
    assert len(state.closed_trades) == 1
    t = state.closed_trades[0]
    assert t.entry_bar == 2
    assert t.entry_price == pytest.approx(120.0)  # open[2]
    assert t.exit_bar == 4
    assert t.exit_price == pytest.approx(140.0)  # open[4]

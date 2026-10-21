"""같은 indicator 사건의 앱 백테스트와 독립 선물 원장을 직접 대조한다."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from scripts.pine_validation.futures import simulate_futures
from scripts.validate_pine_signals import bind_events, execute_pine
from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2


def _source(buy: str, sell: str, long_exit: str = "false", short_exit: str = "false") -> str:
    return f"""//@version=5
indicator("Shared signals")
buy = {buy}
sell = {sell}
longExit = {long_exit}
shortExit = {short_exit}
alertcondition(buy, "Buy", "BUY")
alertcondition(sell, "Sell", "SELL")
alertcondition(longExit, "Close long", "close long")
alertcondition(shortExit, "Close short", "close short")
"""


def _ohlcv(bars: int) -> pd.DataFrame:
    opens = [10 * (i + 1) for i in range(bars)]
    closes = [value + (1 if i % 2 == 0 else -1) for i, value in enumerate(opens)]
    return pd.DataFrame(
        {
            "open": opens,
            "high": [max(a, b) + 1 for a, b in zip(opens, closes, strict=True)],
            "low": [min(a, b) - 1 for a, b in zip(opens, closes, strict=True)],
            "close": closes,
            "volume": 1,
        },
        index=pd.date_range("2026-01-01", periods=bars, freq="h", tz="UTC"),
    )


def _events(source: str, frame: pd.DataFrame):
    result = execute_pine(source, frame, {}, "1h")
    return bind_events(
        result.signal_trace,
        [
            {"function": "alertcondition", "line": line, "direction": direction}
            for line, direction in enumerate(("long", "short", "long_exit", "short_exit"), 7)
        ],
        "1h",
    )


@pytest.mark.parametrize(
    ("source", "bars"),
    [
        (_source("bar_index % 2 == 0", "bar_index % 2 == 1"), 5),
        (
            _source(
                "bar_index == 0 or bar_index == 5", "bar_index == 2", short_exit="bar_index == 3"
            ),
            6,
        ),
        (_source("bar_index == 0 or bar_index == 2", "bar_index == 4"), 6),
        (_source("bar_index == 0 or bar_index == 2", "false", long_exit="bar_index == 2"), 6),
        (_source("true", "false", long_exit="bar_index == 2"), 6),
        (_source("bar_index % 2 == 0", "bar_index % 2 == 1") + "buy := false\nsell := false\n", 5),
        (_source("bar_index == 4", "false"), 5),
    ],
)
def test_indicator_next_open_app_trades_match_independent_futures_ledger(
    source: str, bars: int
) -> None:
    frame = _ohlcv(bars)
    ledger = simulate_futures(frame, _events(source, frame))
    outcome = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open"),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    closed = [trade for trade in outcome.result.trades if trade.status == "closed"]
    assert len(closed) == len(ledger.trades)
    for actual, expected in zip(closed, ledger.trades, strict=True):
        assert actual.direction == expected.direction
        assert frame.index[actual.entry_bar_index] == expected.entry_time
        assert actual.exit_bar_index is not None
        assert frame.index[actual.exit_bar_index] == expected.exit_time
        assert actual.entry_price == expected.entry_price
        assert actual.exit_price == expected.exit_price
        assert actual.size == expected.qty
        assert actual.pnl == expected.pnl
    assert sum((trade.pnl for trade in closed), Decimal("0")) == ledger.realized_pnl
    opened = [trade for trade in outcome.result.trades if trade.status == "open"]
    assert len(opened) == int(ledger.open_position is not None)
    if ledger.open_position is not None:
        assert opened[0].direction == ledger.open_position.direction
        assert frame.index[opened[0].entry_bar_index] == ledger.open_position.entry_time
        assert opened[0].entry_price == ledger.open_position.entry_price
        assert opened[0].size == ledger.open_position.qty


def test_indicator_conflicting_next_open_entries_fail_before_any_fill() -> None:
    source = _source("bar_index == 0", "bar_index == 0")
    frame = _ohlcv(3)
    with pytest.raises(ValueError, match="충돌"):
        simulate_futures(frame, _events(source, frame))
    outcome = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open"),
    )
    assert outcome.status == "error"
    assert "충돌" in str(outcome.error)


@pytest.mark.parametrize("track", ["A", "S"])
@pytest.mark.parametrize(
    ("frequency", "period"),
    [("1min", "1"), ("5min", "5"), ("15min", "15"), ("1h", "60"), ("4h", "240"), ("1D", "D")],
)
def test_app_backtest_passes_real_timeframe_context(
    track: str, frequency: str, period: str
) -> None:
    condition = f'timeframe.period == "{period}" and bar_index == 0'
    source = (
        _source(condition, "false")
        if track == "A"
        else f"""//@version=5
strategy("Context")
if {condition}
    strategy.entry("L", strategy.long)
"""
    )
    frame = _ohlcv(3)
    frame.index = pd.date_range("2026-01-01", periods=3, freq=frequency, tz="UTC")
    outcome = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq=frequency, fill_timing="next_bar_open"),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    assert len(outcome.result.trades) == 1
    assert outcome.result.trades[0].entry_bar_index == 1
    assert outcome.result.trades[0].entry_price == Decimal("20")


def test_native_alert_occurrences_match_app_next_open_fills() -> None:
    source = """//@version=5
indicator("Actual alerts")
if bar_index == 0
    alert("BUY")
if bar_index == 2
    alert("SELL")
"""
    frame = _ohlcv(5)
    trace = execute_pine(source, frame, {}, "1h")
    events = bind_events(
        trace.signal_trace,
        [
            {"function": "alert", "line": 4, "direction": "long"},
            {"function": "alert", "line": 6, "direction": "short"},
        ],
        "1h",
    )
    ledger = simulate_futures(frame, events)
    outcome = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open"),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    assert len(outcome.result.trades) == 2
    closed, opened = outcome.result.trades
    assert closed.entry_price == ledger.trades[0].entry_price
    assert closed.exit_price == ledger.trades[0].exit_price
    assert ledger.open_position is not None
    assert opened.entry_price == ledger.open_position.entry_price


def test_app_closed_pnl_matches_decimal_ledger_for_fractional_prices() -> None:
    source = _source("bar_index == 0", "bar_index == 2")
    frame = _ohlcv(5)
    prices = [100.0, 100.1, 100.2, 100.3, 100.4]
    for column in ("open", "close"):
        frame[column] = prices
    frame["high"] = [price + 1 for price in prices]
    frame["low"] = [price - 1 for price in prices]
    ledger = simulate_futures(frame, _events(source, frame))
    outcome = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open"),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    assert outcome.result.trades[0].pnl == ledger.trades[0].pnl == Decimal("0.2")

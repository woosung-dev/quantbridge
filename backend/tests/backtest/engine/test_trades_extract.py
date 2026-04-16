"""extract_trades() — vectorbt Portfolio → RawTrade list."""
from __future__ import annotations

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
import vectorbt as vbt

from src.backtest.engine.trades import _resolve_bar_index, extract_trades
from src.backtest.engine.types import RawTrade


def test_resolve_bar_index_with_int():
    idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    assert _resolve_bar_index(3, idx) == 3
    assert _resolve_bar_index(np.int64(5), idx) == 5


def test_resolve_bar_index_with_timestamp():
    idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    ts = pd.Timestamp("2024-01-01 03:00:00", tz="UTC")
    assert _resolve_bar_index(ts, idx) == 3


def test_resolve_bar_index_with_duplicate_timestamp_returns_first():
    times = [
        pd.Timestamp("2024-01-01 00:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),  # duplicate
        pd.Timestamp("2024-01-01 02:00:00", tz="UTC"),
    ]
    idx = pd.DatetimeIndex(times)
    ts = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")
    assert _resolve_bar_index(ts, idx) == 1


def test_resolve_bar_index_with_non_monotonic_duplicate_returns_first_true():
    """Non-monotonic index with duplicates → get_loc returns bool ndarray.

    np.argmax(bool_array) returns first True index, ties broken toward smallest.
    """
    times = [
        pd.Timestamp("2024-01-01 00:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 02:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 01:00:00", tz="UTC"),
    ]
    idx = pd.DatetimeIndex(times)
    ts = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")
    assert _resolve_bar_index(ts, idx) == 2


def test_resolve_bar_index_missing_raises_keyerror():
    idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    ts = pd.Timestamp("2030-01-01", tz="UTC")
    with pytest.raises(KeyError):
        _resolve_bar_index(ts, idx)


@pytest.fixture
def simple_portfolio() -> vbt.Portfolio:
    close = pd.Series([100.0, 101.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0])
    entries = pd.Series([True, False, False, False, True, False, False, False])
    exits = pd.Series([False, False, True, False, False, False, True, False])
    return vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.001)


class TestExtractTrades:
    def test_returns_list_of_raw_trade(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        assert isinstance(trades, list)
        assert len(trades) == 2
        for t in trades:
            assert isinstance(t, RawTrade)

    def test_decimal_precision(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        assert all(isinstance(t.entry_price, Decimal) for t in trades)
        assert all(isinstance(t.pnl, Decimal) for t in trades)
        assert all(isinstance(t.fees, Decimal) for t in trades)

    def test_fees_decimal_first_sum(self, simple_portfolio: vbt.Portfolio) -> None:
        """fees = Decimal(entry) + Decimal(exit). float 공간 합산 금지."""
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        assert all(t.fees > Decimal("0") for t in trades)

    def test_closed_trades_have_exit(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        closed = [t for t in trades if t.status == "closed"]
        for t in closed:
            assert t.exit_bar_index is not None
            assert t.exit_price is not None

    def test_direction_lowercase(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        for t in trades:
            assert t.direction in ("long", "short")

    def test_empty_trades(self) -> None:
        """signals 없는 portfolio → 빈 list."""
        close = pd.Series([100.0, 101.0, 102.0])
        entries = pd.Series([False, False, False])
        exits = pd.Series([False, False, False])
        pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000)
        ohlcv = pd.DataFrame({"close": close})
        trades = extract_trades(pf, ohlcv)
        assert trades == []

    def test_bar_index_matches_vectorbt(self, simple_portfolio: vbt.Portfolio) -> None:
        """entry_bar_index / exit_bar_index는 vectorbt 출력 정확히 보존."""
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        df = simple_portfolio.trades.records_readable
        for i, t in enumerate(trades):
            assert t.entry_bar_index == int(df.iloc[i]["Entry Timestamp"])
            if t.status == "closed":
                assert t.exit_bar_index == int(df.iloc[i]["Exit Timestamp"])

    def test_bar_index_with_datetime_index(self) -> None:
        """Sprint 5 M3 TimescaleDB 시나리오: DatetimeIndex 기반 OHLCV에서도
        entry_bar_index / exit_bar_index가 정수 위치로 정규화되어야 한다.

        vectorbt는 DatetimeIndex가 주어지면 Timestamp를 반환하므로, ohlcv.index.get_loc()
        로 정수 위치를 구한 값과 일치해야 한다.
        """
        idx = pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC")
        close = pd.Series([100.0, 101.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0], index=idx)
        entries = pd.Series([True, False, False, False, True, False, False, False], index=idx)
        exits = pd.Series([False, False, True, False, False, False, True, False], index=idx)
        pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.001)
        ohlcv = pd.DataFrame({"close": close}, index=idx)

        trades = extract_trades(pf, ohlcv)
        assert len(trades) == 2

        df = pf.trades.records_readable
        for i, t in enumerate(trades):
            expected_entry = ohlcv.index.get_loc(df.iloc[i]["Entry Timestamp"])
            assert isinstance(t.entry_bar_index, int)
            assert t.entry_bar_index == expected_entry
            if t.status == "closed":
                expected_exit = ohlcv.index.get_loc(df.iloc[i]["Exit Timestamp"])
                assert isinstance(t.exit_bar_index, int)
                assert t.exit_bar_index == expected_exit

    def test_negative_return_pct_losing_trade(self) -> None:
        """손실 거래도 정확히 처리되어야 함 (return_pct < 0)."""
        close = pd.Series([100.0, 102.0, 101.0, 99.0, 97.0, 95.0])
        entries = pd.Series([True, False, False, False, False, False])
        exits = pd.Series([False, False, False, False, False, True])
        pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.001)
        ohlcv = pd.DataFrame({"close": close}, index=close.index)

        trades = extract_trades(pf, ohlcv)
        assert len(trades) == 1
        assert trades[0].return_pct < Decimal("0")
        assert trades[0].pnl < Decimal("0")

"""extract_trades() — vectorbt Portfolio → RawTrade list."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest
import vectorbt as vbt

from src.backtest.engine.trades import extract_trades
from src.backtest.engine.types import RawTrade


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

"""Portfolio → BacktestMetrics 추출기 검증."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest
import vectorbt as vbt

from src.backtest.engine.metrics import extract_metrics
from src.backtest.engine.types import BacktestMetrics


def _run_vbt(entries, exits, close=None):
    if close is None:
        close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0, 12.5])
    return vbt.Portfolio.from_signals(
        close=close,
        entries=pd.Series(entries),
        exits=pd.Series(exits),
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )


def test_extract_metrics_returns_all_five_fields():
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert isinstance(m, BacktestMetrics)
    assert isinstance(m.total_return, Decimal)
    assert isinstance(m.sharpe_ratio, Decimal)
    assert isinstance(m.max_drawdown, Decimal)
    assert isinstance(m.win_rate, Decimal)
    assert isinstance(m.num_trades, int)


def test_extract_metrics_zero_trades_gives_zero_win_rate():
    pf = _run_vbt(
        entries=[False, False, False, False, False, False],
        exits=[False, False, False, False, False, False],
    )
    m = extract_metrics(pf)
    assert m.num_trades == 0
    assert m.win_rate == Decimal("0")


def test_extract_metrics_num_trades_is_integer():
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert m.num_trades == 1

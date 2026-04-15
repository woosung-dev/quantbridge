"""S3-02: 중복 strategy.exit 호출 시 warnings 기록."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine import parse_and_run


def _ohlcv(n: int = 40) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    close = pd.Series(np.linspace(100, 140, n), index=idx)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": pd.Series(1000.0, index=idx),
        }
    )


def test_duplicate_strategy_exit_emits_warning():
    source = """//@version=5
strategy("dup exit")
long = ta.crossover(close, ta.sma(close, 5))
flat = ta.crossunder(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
if flat
    strategy.close("L")
strategy.exit("x1", stop=close * 0.95)
strategy.exit("x2", stop=close * 0.90)
"""
    outcome = parse_and_run(source, _ohlcv())
    assert outcome.status == "ok", outcome
    assert outcome.signals is not None
    warnings = outcome.signals.warnings
    assert any("duplicate strategy.exit" in w for w in warnings), warnings


def test_single_strategy_exit_has_no_warning():
    source = """//@version=5
strategy("single exit")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
strategy.exit("x", stop=close * 0.95)
"""
    outcome = parse_and_run(source, _ohlcv())
    assert outcome.status == "ok"
    assert outcome.signals is not None
    assert outcome.signals.warnings == []

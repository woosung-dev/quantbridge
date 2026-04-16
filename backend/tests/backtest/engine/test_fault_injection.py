"""S3-03: engine exception 분기 fault injection.

목표: src/backtest/engine/* 커버리지 91% → 95% (non-blocking stretch).
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.backtest.engine import run_backtest

SIMPLE_PINE_V5 = """//@version=5
strategy("T", overlay=true)
ema_fast = ta.ema(close, 10)
ema_slow = ta.ema(close, 30)
if ta.crossover(ema_fast, ema_slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(ema_fast, ema_slow)
    strategy.close("L")
"""


@pytest.fixture
def valid_ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=100, freq="1h")
    return pd.DataFrame(
        {
            "open": range(100, 200),
            "high": range(101, 201),
            "low": range(99, 199),
            "close": range(100, 200),
            "volume": [100.0] * 100,
        },
        index=idx,
    )


class TestRunBacktestFaultInjection:
    def test_vectorbt_exception_becomes_error(self, valid_ohlcv: pd.DataFrame) -> None:
        """vbt.Portfolio.from_signals 예외 → BacktestOutcome(status='error')."""
        with patch("src.backtest.engine.vbt.Portfolio.from_signals", side_effect=RuntimeError("vbt boom")):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"
        assert outcome.result is None
        assert "vbt boom" in str(outcome.error)

    def test_extract_metrics_exception(self, valid_ohlcv: pd.DataFrame) -> None:
        """extract_metrics 예외 → error status."""
        with patch("src.backtest.engine.extract_metrics", side_effect=ValueError("metrics fail")):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"
        assert "metrics fail" in str(outcome.error)

    def test_extract_trades_exception(self, valid_ohlcv: pd.DataFrame) -> None:
        """extract_trades 예외 → error status."""
        with patch("src.backtest.engine.extract_trades", side_effect=RuntimeError("trades boom")):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"
        assert "trades boom" in str(outcome.error)

    def test_parse_and_run_returns_unsupported(self, valid_ohlcv: pd.DataFrame) -> None:
        """파서가 unsupported 반환 → parse_failed."""
        # qty_percent 는 Sprint 1 파서에서 deferred(unsupported)로 처리됨
        unsupported_pine = """//@version=5
strategy("X")
strategy.entry("L", strategy.long, qty_percent=10)
"""
        outcome = run_backtest(unsupported_pine, valid_ohlcv)
        assert outcome.status == "parse_failed"
        assert outcome.result is None

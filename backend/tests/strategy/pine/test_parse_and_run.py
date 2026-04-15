"""parse_and_run() 통합 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine import parse_and_run


def _ohlcv(n: int = 20) -> pd.DataFrame:
    close = pd.Series(np.linspace(10.0, 30.0, n))
    return pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": [100.0] * n,
    })


def test_empty_source_returns_ok():
    outcome = parse_and_run("", _ohlcv())
    assert outcome.status == "ok"
    assert outcome.result is not None
    assert not outcome.result.entries.any()
    assert outcome.source_version == "v5"


def test_simple_v5_ema_cross_returns_ok():
    src = """//@version=5
strategy("X")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "ok"
    assert outcome.source_version == "v5"
    assert "ta.ema" in outcome.supported_feature_report["functions_used"]


def test_v4_ema_cross_auto_migrated_and_ok():
    src = """//@version=4
strategy("X")
fast = ema(close, 3)
slow = ema(close, 8)
if crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if crossunder(fast, slow)
    strategy.close("Long")
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "ok"
    assert outcome.source_version == "v4"


def test_unsupported_function_returns_unsupported_status():
    src = """//@version=5
x = ta.vwma(close, 20)
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert outcome.error.feature == "ta.vwma"


def test_syntax_error_returns_error_status():
    src = "x = = 1\n"
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "error"
    assert outcome.error is not None


def test_strategy_exit_with_bracket_returns_unsupported():
    src = """//@version=5
strategy("X")
if close > 15
    strategy.entry("Long", strategy.long)
strategy.exit("tp", "Long", stop=close - 1, limit=close + 1)
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "bracket" in str(outcome.error).lower() or outcome.error.feature.startswith("strategy.exit")

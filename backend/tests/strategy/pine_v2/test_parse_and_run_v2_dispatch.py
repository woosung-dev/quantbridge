"""Sprint 8c — 3-Track dispatcher (parse_and_run_v2) 단위."""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2 import V2RunResult, parse_and_run_v2


def _ohlcv(n: int = 5) -> pd.DataFrame:
    closes = [10.0 + i for i in range(n)]
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1.0] * n,
    })


def test_dispatch_strategy_routes_to_track_s() -> None:
    src = 'strategy("T", overlay=true)\nx = close\n'
    result = parse_and_run_v2(src, _ohlcv())
    assert isinstance(result, V2RunResult)
    assert result.track == "S"
    assert result.historical is not None
    assert result.virtual is None


def test_dispatch_indicator_with_alert_routes_to_track_a() -> None:
    src = 'indicator("T")\nalertcondition(close > 10, "up")\n'
    result = parse_and_run_v2(src, _ohlcv())
    assert result.track == "A"
    assert result.virtual is not None
    assert result.historical is None


def test_dispatch_indicator_without_alert_routes_to_track_m() -> None:
    src = 'indicator("T")\nx = close + 1\n'
    result = parse_and_run_v2(src, _ohlcv())
    assert result.track == "M"
    assert result.historical is not None


def test_track_s_result_exposes_strategy_state() -> None:
    src = 'strategy("T", overlay=true)\nx = close\n'
    result = parse_and_run_v2(src, _ohlcv())
    assert result.historical is not None
    assert result.historical.strategy_state is not None
    # StrategyState: open_trades/closed_trades dict 구조
    assert hasattr(result.historical.strategy_state, "open_trades")
    assert hasattr(result.historical.strategy_state, "closed_trades")


def test_track_m_result_exposes_var_series() -> None:
    src = 'indicator("T")\nx = close + 1\n'
    result = parse_and_run_v2(src, _ohlcv())
    assert result.historical is not None
    vs = result.historical.var_series
    assert isinstance(vs, dict)
    assert "x" in vs
    assert vs["x"] == pytest.approx([11.0, 12.0, 13.0, 14.0, 15.0])

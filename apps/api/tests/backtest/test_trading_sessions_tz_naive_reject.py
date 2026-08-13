# Sprint 38 BL-188 v3 A2 — trading_sessions + tz-naive index → 422 fail-closed reject 검증
"""sessions 활성 시 OHLCV index 가 tz-naive 또는 non-DatetimeIndex 면 v2_adapter 가
TradingSessionTzNaiveReject (422) raise — silent UTC 가정 차단.

회귀 invariants:
- sessions=() 비어있으면 reject 안 함 (naive index 도 통과).
- sessions 활성 + naive DatetimeIndex → reject.
- sessions 활성 + non-DatetimeIndex (RangeIndex 등) → reject.
- sessions 활성 + tz-aware DatetimeIndex → 정상 실행.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.backtest.exceptions import TradingSessionTzNaiveReject

_PINE_S_BARE = """//@version=5
strategy("S-Bare", overlay=true)
"""


def _ohlcv(idx: pd.Index) -> pd.DataFrame:
    n = len(idx)
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [1.0] * n,
        },
        index=idx,
    )


def test_sessions_active_naive_index_rejects_422() -> None:
    """sessions=("asia",) + naive DatetimeIndex → TradingSessionTzNaiveReject."""
    naive_idx = pd.date_range("2026-04-01 00:00:00", periods=24, freq="1h")
    cfg = BacktestConfig(trading_sessions=("asia",))
    with pytest.raises(TradingSessionTzNaiveReject) as ei:
        run_backtest_v2(_PINE_S_BARE, _ohlcv(naive_idx), cfg)
    assert ei.value.status_code == 422
    assert "tz-aware" in (ei.value.detail or "")


def test_sessions_active_non_datetime_index_rejects_422() -> None:
    """sessions=("london",) + RangeIndex → TradingSessionTzNaiveReject."""
    range_idx = pd.RangeIndex(start=0, stop=24)
    cfg = BacktestConfig(trading_sessions=("london",))
    with pytest.raises(TradingSessionTzNaiveReject) as ei:
        run_backtest_v2(_PINE_S_BARE, _ohlcv(range_idx), cfg)
    assert ei.value.status_code == 422
    assert "DatetimeIndex" in (ei.value.detail or "")


def test_sessions_empty_no_reject_on_naive_index() -> None:
    """sessions=() 비어있으면 naive index 라도 reject 안 함 (회귀 0)."""
    naive_idx = pd.date_range("2026-04-01 00:00:00", periods=10, freq="1h")
    cfg = BacktestConfig(trading_sessions=())
    out = run_backtest_v2(_PINE_S_BARE, _ohlcv(naive_idx), cfg)
    assert out.status == "ok", f"sessions 비어있는데 reject — 회귀: {out.error}"


def test_sessions_active_tz_aware_index_passes() -> None:
    """sessions=("ny",) + tz-aware DatetimeIndex → 정상 실행."""
    tz_idx = pd.date_range("2026-04-01 00:00:00+00:00", periods=10, freq="1h")
    cfg = BacktestConfig(trading_sessions=("ny",))
    out = run_backtest_v2(_PINE_S_BARE, _ohlcv(tz_idx), cfg)
    assert out.status == "ok", f"tz-aware index 인데 fail: {out.error}"

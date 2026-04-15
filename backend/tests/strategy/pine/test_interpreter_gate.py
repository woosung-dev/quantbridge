"""S3-01: if-branch 내부의 strategy.exit는 gate 조건을 SL/TP에 반영해야 함."""
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


def test_strategy_exit_inside_if_respects_gate():
    """entry가 gate 경계 이전(bar_index==5)에 발생하고,
    stop이 gate 이후(bar_index>20)에만 설정되면
    진입 바(bar_index=5)의 stop_series는 NaN이어야 하므로
    sl_stop carry-forward도 NaN이어야 한다."""
    source = """//@version=5
strategy("gated exit")
if bar_index == 5
    strategy.entry("L", strategy.long)

late = bar_index > 20
if late
    strategy.exit("x", stop=close * 0.95)
"""
    ohlcv = _ohlcv(40)
    outcome = parse_and_run(source, ohlcv)
    assert outcome.status == "ok", outcome
    sr = outcome.signals
    assert sr is not None

    # 진입은 bar_index=5에서 발생해야 함
    assert sr.entries.iloc[5] is True or bool(sr.entries.iloc[5])

    sl = sr.sl_stop
    assert sl is not None

    # gate(bar_index>20)가 적용되면 진입 바(bar_index=5)의 stop_series=NaN
    # → carry_bracket이 NaN을 ffill → 전체 sl_stop이 NaN이어야 함
    finite_values = sl.dropna()
    assert len(finite_values) == 0, (
        f"sl_stop should be all NaN when entry occurs before gate activates; "
        f"got non-NaN at bars: {list(finite_values.index)}"
    )

"""strategy.exit(stop=, limit=) 해금 후 SignalResult 브래킷 필드 채움 검증."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine import parse_and_run


def _ohlcv(close_values: list[float]) -> pd.DataFrame:
    n = len(close_values)
    close = pd.Series(close_values, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": pd.Series([100.0] * n),
        }
    )


def test_strategy_exit_stop_limit_produces_bracket_series():
    """한 번의 long 포지션 동안 sl_stop/tp_limit이 carry forward 되고, 청산 후 NaN."""
    src = """//@version=5
strategy("bracket")
entry_cond = bar_index == 2
exit_cond = bar_index == 5
if entry_cond
    strategy.entry("Long", strategy.long)
if exit_cond
    strategy.close("Long")
strategy.exit("Exit", stop=close * 0.9, limit=close * 1.1)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok", f"expected ok, got {outcome.status}: {outcome.error}"
    signal = outcome.result
    assert signal is not None

    # bar:  0  1  2  3  4  5  6  7
    # ent:  0  0  1  0  0  0  0  0  cumsum: 0 0 1 1 1 1 1 1
    # ext:  0  0  0  0  0  1  0  0  cumsum: 0 0 0 0 0 1 1 1
    # pos:  0  0  1  1  1  0  0  0
    assert signal.sl_stop is not None
    assert signal.tp_limit is not None

    expected_sl = [math.nan, math.nan, 12.0 * 0.9, 12.0 * 0.9, 12.0 * 0.9, math.nan, math.nan, math.nan]
    expected_tp = [math.nan, math.nan, 12.0 * 1.1, 12.0 * 1.1, 12.0 * 1.1, math.nan, math.nan, math.nan]

    np.testing.assert_allclose(signal.sl_stop.to_numpy(), expected_sl, equal_nan=True)
    np.testing.assert_allclose(signal.tp_limit.to_numpy(), expected_tp, equal_nan=True)


def test_strategy_exit_only_stop_leaves_tp_limit_none():
    """stop= 만 주면 tp_limit Series는 None 유지."""
    src = """//@version=5
strategy("stop only")
if bar_index == 1
    strategy.entry("Long", strategy.long)
if bar_index == 3
    strategy.close("Long")
strategy.exit("Exit", stop=close * 0.95)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0, 13.0, 14.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok"
    signal = outcome.result
    assert signal is not None
    assert signal.sl_stop is not None
    assert signal.tp_limit is None


def test_strategy_exit_no_args_still_unsupported():
    """stop/limit 둘 다 없으면 여전히 Unsupported."""
    src = """//@version=5
strategy("bare exit")
if bar_index == 1
    strategy.entry("Long", strategy.long)
strategy.exit("Exit")
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "strategy.exit" in outcome.error.feature


def test_strategy_entry_qty_literal_populates_position_size():
    """strategy.entry(qty=2) 리터럴 → position_size는 2.0 상수 Series."""
    src = """//@version=5
strategy("qty literal")
if bar_index == 1
    strategy.entry("Long", strategy.long, qty=2)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok"
    signal = outcome.result
    assert signal is not None
    assert signal.position_size is not None
    np.testing.assert_allclose(signal.position_size.to_numpy(), [2.0, 2.0, 2.0])


def test_strategy_entry_without_qty_leaves_position_size_none():
    """qty 생략 → position_size None 유지 (vectorbt 기본값 사용 예정)."""
    src = """//@version=5
strategy("no qty")
if bar_index == 1
    strategy.entry("Long", strategy.long)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok"
    signal = outcome.result
    assert signal is not None
    assert signal.position_size is None


def test_strategy_short_entry_is_unsupported():
    """strategy.entry(direction=strategy.short)는 Sprint 2에서 Unsupported."""
    src = """//@version=5
strategy("short")
if bar_index == 1
    strategy.entry("Short", strategy.short)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "short" in outcome.error.feature.lower()


def test_strategy_entry_qty_percent_is_unsupported():
    """qty_percent= 는 Sprint 2에서 Unsupported."""
    src = """//@version=5
strategy("qty percent")
if bar_index == 1
    strategy.entry("Long", strategy.long, qty_percent=50)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "qty_percent" in outcome.error.feature


def test_strategy_entry_qty_non_literal_is_unsupported():
    """qty=<expression> (non-literal)은 Sprint 2에서 Unsupported."""
    src = """//@version=5
strategy("qty expr")
sz = 2
if bar_index == 1
    strategy.entry("Long", strategy.long, qty=sz)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "qty" in outcome.error.feature.lower()

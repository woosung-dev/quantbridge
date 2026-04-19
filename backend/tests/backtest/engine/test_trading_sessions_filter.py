"""Sprint 7d — run_backtest가 cfg.trading_sessions로 entries를 마스킹.

vectorbt 전체 실행 대신 helper (`_build_session_hour_mask`, `_apply_trading_sessions`)
를 직접 검증한다. run_backtest 경로는 OHLCV/Pine 스크립트 조합이 많아 간접 검증으로
충분하며 회귀는 test_run_backtest.py와 test_golden_backtest.py가 담당.
"""
from __future__ import annotations

import pandas as pd

from src.backtest.engine import _apply_trading_sessions, _build_session_hour_mask
from src.strategy.pine.types import SignalResult


def _hourly_index(start_utc_hour: int = 0, n: int = 24) -> pd.DatetimeIndex:
    return pd.date_range(
        f"2026-04-19 {start_utc_hour:02d}:00:00+00:00",
        periods=n,
        freq="h",
    )


def test_build_session_hour_mask_utc_index():
    idx = _hourly_index()
    mask = _build_session_hour_mask(idx, ("asia",))
    # asia = [0,7)
    assert mask.iloc[0] is True or bool(mask.iloc[0]) is True  # hour 0
    assert bool(mask.iloc[6]) is True  # hour 6
    assert bool(mask.iloc[7]) is False  # hour 7 (exclusive)
    assert bool(mask.iloc[14]) is False  # hour 14
    assert bool(mask.iloc[23]) is False


def test_build_session_hour_mask_multiple_sessions():
    idx = _hourly_index()
    mask = _build_session_hour_mask(idx, ("asia", "ny"))
    # asia[0,7) + ny[13,20)
    assert bool(mask.iloc[5]) is True
    assert bool(mask.iloc[10]) is False  # no coverage
    assert bool(mask.iloc[15]) is True  # ny


def test_build_session_hour_mask_naive_index_treated_as_utc():
    idx = pd.date_range("2026-04-19 00:00:00", periods=24, freq="h")
    assert idx.tz is None
    mask = _build_session_hour_mask(idx, ("london",))
    # london[8,16)
    assert bool(mask.iloc[8]) is True
    assert bool(mask.iloc[15]) is True
    assert bool(mask.iloc[16]) is False


def test_build_session_hour_mask_unknown_name_skipped():
    idx = _hourly_index(n=3)  # 00, 01, 02
    mask = _build_session_hour_mask(idx, ("bogus",))
    assert not mask.any()


def test_apply_trading_sessions_masks_entries_in_place():
    idx = _hourly_index()
    entries = pd.Series([True] * 24, index=idx)
    exits = pd.Series([False] * 24, index=idx)
    signal = SignalResult(entries=entries, exits=exits)

    _apply_trading_sessions(signal, ("london",))

    # london[8,16): hours 8..15 → True, others False
    allowed_hours = set(range(8, 16))
    for i, ts in enumerate(idx):
        expected = ts.hour in allowed_hours
        assert bool(signal.entries.iloc[i]) is expected, (
            f"hour={ts.hour} expected={expected} got={signal.entries.iloc[i]}"
        )

    # exits는 건드리지 않음
    assert not signal.exits.any()


def test_apply_trading_sessions_noop_on_non_datetime_index():
    entries = pd.Series([True, True, True])
    exits = pd.Series([False, False, False])
    signal = SignalResult(entries=entries, exits=exits)

    _apply_trading_sessions(signal, ("london",))
    # 그대로
    assert signal.entries.tolist() == [True, True, True]

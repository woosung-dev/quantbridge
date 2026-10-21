"""C 원문의 상태 경계 손계산. 실제 Pine 대조는 독립 계산 구현 밖에서 수행한다."""

import numpy as np
import pandas as pd
import pytest

from scripts.pine_validation.oracles_c import (
    everget_supertrend,
    everget_supertrend_values,
    qqe_primary_zero_cross,
    rsi_signals_entries,
)


def frame(prices):
    prices = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {"open": prices - 1, "high": prices + 1, "low": prices - 1, "close": prices, "volume": 1},
        index=pd.date_range("2020-01-01", periods=len(prices), freq="h", tz="UTC"),
    )


def positions(events, data):
    return [(data.index.get_loc(event.bar_time), event.direction) for event in events]


def test_rsi_extreme_fires_once_until_zone_is_left():
    data = frame([10, 11, 12, 11, 10, 11])
    assert positions(rsi_signals_entries(data, {"rsi_length": 1}), data) == [
        (1, "short"),
        (3, "long"),
        (5, "short"),
    ]


def test_rsi_support_waits_for_strong_bullish_candle_after_zone_entry():
    data = frame([10, 12, 14, 13, 12, 14])
    data["open"] = [10, 11, 13, 14, 13, 11]
    params = {
        "rsi_length": 2,
        "over_buy": 99,
        "resistance": 90,
        "support": 80,
        "over_sold": 10,
        "strong_lookback": 2,
        "strong_multiplier": 1.2,
    }
    # RSI 100, 66.67, 40, 76.92: support에 들어간 3번이 아니라 강한 양봉 5번에서 매수.
    assert positions(rsi_signals_entries(data, params), data) == [(2, "short"), (5, "long")]


def test_everget_wicks_can_reverse_twice_without_close_cross():
    data = frame([10, 10, 10])
    data["open"], data["high"], data["low"] = [10, 10, 10], [11, 11, 13], [9, 7, 9]
    params = {"atr_period": 1, "factor": 1}
    lower, upper, direction = everget_supertrend_values(data, **params)
    np.testing.assert_allclose(lower, [8, 8, 7])
    np.testing.assert_allclose(upper, [12, 12, 12])
    assert direction.tolist() == [1, -1, 1]
    assert positions(everget_supertrend(data, params), data) == [(1, "short"), (2, "long")]
    assert everget_supertrend(data, {**params, "wicks": False}) == []


def test_everget_four_price_doji_preserves_both_previous_stops():
    data = frame([10, 10])
    data["open"], data["high"], data["low"] = [10, 10], [11, 10], [9, 10]
    lower, upper, _ = everget_supertrend_values(data, atr_period=1, factor=1)
    np.testing.assert_allclose(lower, [8, 8])
    np.testing.assert_allclose(upper, [12, 12])


def test_qqe_uses_primary_rsi_zero_alerts_not_histogram_thresholds():
    data = frame([10, 11, 10, 11])
    params = {"rsi_length": 1, "rsi_smoothing": 1}
    assert positions(qqe_primary_zero_cross(data, params), data) == [(2, "short"), (3, "long")]


@pytest.mark.parametrize(
    "oracle", [rsi_signals_entries, everget_supertrend, qqe_primary_zero_cross]
)
def test_future_suffix_does_not_change_prior_events(oracle):
    data = frame(100 + 10 * np.sin(np.arange(220) * 0.3))
    assert oracle(data.iloc[:110], {}) == [
        event for event in oracle(data, {}) if event.bar_time < data.index[110]
    ]

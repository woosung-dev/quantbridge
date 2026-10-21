"""원문 B 계산의 손계산 경계 및 지원 엔진과의 독립 대조."""

import numpy as np
import pandas as pd
import pytest

from scripts.pine_validation.oracles_b import (
    gann_high_low,
    parabolic_sar_values,
    stochastic_kd,
    trend_magic,
)


def frame(prices):
    prices = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {"open": prices, "high": prices + 1, "low": prices - 1, "close": prices, "volume": 1},
        index=pd.date_range("2020-01-01", periods=len(prices), freq="h", tz="UTC"),
    )


def positions(events, data):
    return [(data.index.get_loc(event.bar_time), event.direction) for event in events]


def test_gann_keeps_state_until_previous_band_is_broken():
    data = frame([10, 11, 12, 9, 8, 11, 12])
    events = gann_high_low(data, {"high_period": 2, "low_period": 2})
    assert positions(events, data) == [(3, "short"), (5, "long")]


def test_stochastic_crossover_is_hidden_when_numeric_marker_is_zero():
    data = frame([2, 3, 1, 2, 3, 1])
    data["high"], data["low"] = 3, 1
    params = {"period_k": 2, "smooth_k": 1, "period_d": 2}
    assert positions(stochastic_kd(data, params), data) == [(3, "long")]
    assert stochastic_kd(data, {**params, "highlight_crossovers": False}) == []


def test_sar_seed_and_two_bar_clamp_have_hand_calculated_values():
    np.testing.assert_allclose(parabolic_sar_values(frame([2, 3, 4, 5])), [np.nan, 1, 1, 1.16])


def test_trend_magic_uses_low_high_cross_not_close_cross():
    data = frame([10, 11, 12, 9, 8, 11, 12])
    # 3번 봉 종가는 선 아래지만 high는 선 위다. 종가 교차로 바꾸면 허위 short가 생긴다.
    assert positions(trend_magic(data, {"period": 2, "atr_period": 2}), data) == [(5, "long")]


@pytest.mark.parametrize("oracle", [gann_high_low, stochastic_kd, trend_magic])
def test_future_suffix_cannot_change_preceding_events(oracle):
    data = frame(100 + 10 * np.sin(np.arange(200) * 0.3))
    earlier = oracle(data.iloc[:100], {})
    full = [event for event in oracle(data, {}) if event.bar_time < data.index[100]]
    assert earlier == full


def test_independent_sar_agrees_with_real_pine_on_alternating_trends():
    from scripts.pine_validation.oracles_b import parabolic_sar
    from scripts.validate_pine_signals import bind_events, execute_pine

    source = """//@version=6
indicator("PSAR calculation fixture")
psar = ta.sar(0.02, 0.02, 0.2)
dir = psar < close ? 1 : -1
alertcondition(dir == 1 and dir[1] == -1)
alertcondition(dir == -1 and dir[1] == 1)
"""
    data = frame(100 + 10 * np.sin(np.arange(300) * 0.2))
    result = execute_pine(source, data, {}, "1h")
    assert not result.errors
    events = bind_events(
        result.signal_trace,
        [
            {"function": "alertcondition", "line": 5, "direction": "long"},
            {"function": "alertcondition", "line": 6, "direction": "short"},
        ],
        "1h",
    )
    assert sorted(positions(events, data)) == sorted(positions(parabolic_sar(data, {}), data))
    assert {event.direction for event in events} == {"long", "short"}

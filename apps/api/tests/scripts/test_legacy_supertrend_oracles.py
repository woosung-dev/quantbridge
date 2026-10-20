"""Cloud/v1 원문의 NA 밴드·상승 seed·교차 표식과 전환 alert 차이를 손계산한다."""

from datetime import timedelta

import numpy as np
import pandas as pd

from scripts.pine_validation.oracles import compute_oracle, legacy_supertrend


def candles() -> pd.DataFrame:
    prices = [10, 10, 6, 6, 14]
    return pd.DataFrame(
        {
            "open": prices,
            "high": np.asarray(prices) + 1,
            "low": np.asarray(prices) - 1,
            "close": prices,
            "volume": [1] * len(prices),
        },
        index=pd.date_range("2020-01-01", periods=len(prices), freq="h", tz="UTC"),
    )


def seed_gap() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10, 10, 10, 2, 20],
            "high": [10, 10, 40, 3, 21],
            "low": [10, 10, 1, 1, 19],
            "close": [10, 10, 1, 2, 20],
            "volume": [1] * 5,
        },
        index=pd.date_range("2020-01-01", periods=5, freq="h", tz="UTC"),
    )


def test_first_atr_value_cannot_replace_previous_na_band_and_flip_initial_trend():
    # TR=0,0,39,2,19 → RMA3=NA,NA,13,28/3,113/9.
    line, trend = legacy_supertrend(seed_gap(), factor=1, atr_period=3)
    np.testing.assert_array_equal(trend, [1, 1, 1, -1, 1])
    np.testing.assert_allclose(line, [np.nan, np.nan, 7.5, 34 / 3, 67 / 9], equal_nan=True)


def test_crossed_previous_bands_keep_original_up_condition_priority():
    prices = np.asarray([10] * 10 + [30, 20], dtype=float)
    frame = pd.DataFrame(
        {
            "open": prices,
            "high": prices + 1,
            "low": prices - 1,
            "close": prices,
            "volume": 1,
        },
        index=pd.date_range("2020-01-01", periods=len(prices), freq="h", tz="UTC"),
    )
    # 갭 상승 봉의 이전 lower=26.1, upper=12. 다음 close=20은 두 전환 조건을 모두 충족한다.
    # 원문은 close>upper를 먼저 판정하므로 이전 trend에 따라 down으로 바꾸면 안 된다.
    line, trend = legacy_supertrend(frame, factor=1, atr_period=10)
    np.testing.assert_array_equal(trend, np.ones(len(prices)))
    np.testing.assert_allclose(line[-3:], [8, 26.1, 26.1])


def test_v1_alert_is_trend_reversal_even_when_no_tsl_crossing_occurs():
    frame = seed_gap()
    params = {"factor": 1, "atr_period": 3}
    alerts = compute_oracle("supertrend_v1", frame, params)
    cloud = compute_oracle("supertrend_cloud", frame, {**params, "factor_2": 1, "atr_period_2": 3})
    assert [(event.bar_time, event.direction) for event in alerts] == [
        (frame.index[3], "short"),
        (frame.index[4], "long"),
    ]
    # 이전 close=1은 이전 Tsl=7.5 아래이므로 4번째 봉에서 새로운 하향 교차는 없다.
    assert [(event.bar_time, event.direction) for event in cloud] == [
        (frame.index[4], "long"),
        (frame.index[4], "long"),
    ]


def test_cloud_uses_independent_multiplier_and_crossing_instead_of_trend_change():
    frame = candles()
    secondary, trend = legacy_supertrend(frame, factor=2, atr_period=2)
    np.testing.assert_array_equal(trend, [1, 1, 1, 1, 1])
    np.testing.assert_allclose(secondary, [np.nan, 6, 6, 0.5, 2.25], equal_nan=True)
    events = compute_oracle(
        "supertrend_cloud",
        frame,
        {"factor": 1, "atr_period": 2, "factor_2": 2, "atr_period_2": 2},
    )
    assert [(event.bar_time, event.direction) for event in events] == [
        (frame.index[2], "short"),
        (frame.index[3], "long"),
        (frame.index[4], "long"),
    ]
    assert all(
        event.confirmed_at == event.bar_time + timedelta(hours=1)
        and event.display_time == event.bar_time
        for event in events
    )


def test_cloud_second_atr_period_and_duplicate_conditions_are_not_discarded():
    frame = seed_gap()
    events = compute_oracle(
        "supertrend_cloud",
        frame,
        {"factor": 1, "atr_period": 3, "factor_2": 2, "atr_period_2": 1},
    )
    assert [(event.bar_time, event.direction) for event in events] == [
        (frame.index[2], "short"),
        (frame.index[4], "long"),
        (frame.index[4], "long"),
    ]

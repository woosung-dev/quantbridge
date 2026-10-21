"""실제 수집 원본에서 확인한 수식 차이를 작은 손계산 입력으로 검증한다."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.pine_validation.oracles import compute_oracle, kivanc_supertrend


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


def test_kivanc_initial_uptrend_emits_first_sell_that_builtin_seed_does_not():
    frame = candles()
    line, direction = kivanc_supertrend(frame, factor=1, atr_period=2)
    np.testing.assert_array_equal(direction, [1, 1, -1, -1, 1])
    np.testing.assert_allclose(line, [np.nan, 8, 9.5, 8.75, 8.125], equal_nan=True)
    params = {"factor": 1, "atr_period": 2}
    reviewed = compute_oracle("kivanc_supertrend", frame, params)
    generic = compute_oracle("supertrend", frame, params)
    assert [(event.bar_time, event.direction) for event in reviewed] == [
        (frame.index[2], "short"),
        (frame.index[4], "long"),
    ]
    assert [(event.bar_time, event.direction) for event in generic] == [(frame.index[4], "long")]


def test_kivanc_wick_option_and_sma_option_use_original_input_semantics():
    frame = candles()
    frame.loc[frame.index[1], "low"] = 5
    _, close_only = kivanc_supertrend(frame, factor=1, atr_period=1)
    _, with_wicks = kivanc_supertrend(frame, factor=1, atr_period=1, ignore_wicks=False)
    assert close_only[1] == 1 and with_wicks[1] == -1
    sma_line, _ = kivanc_supertrend(candles(), factor=1, atr_period=2, atr_method="sma")
    np.testing.assert_allclose(sma_line, [np.nan, 8, 9.5, 9.5, 8.5], equal_nan=True)

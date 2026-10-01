"""날짜 필터는 합성 달력이 아니라 입력 캔들 시각을 읽는다."""

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical


@pytest.mark.parametrize("frequency", ["1min", "1h", "4h", "1D"])
def test_time_and_history_follow_actual_candle_timestamps(frequency):
    index = pd.date_range("2026-09-01", periods=3, freq=frequency, tz="Asia/Seoul")
    frame = pd.DataFrame(
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 10.0}, index=index
    )
    result = run_historical(
        '//@version=5\nindicator("clock")\nnow = time\nprevious = time[1]\n', frame
    )
    assert result.final_state["now"] == index[-1].value // 1_000_000
    assert result.final_state["previous"] == index[-2].value // 1_000_000


def test_time_without_timestamps_is_na_not_a_fabricated_date():
    frame = pd.DataFrame(
        {"open": [100.0], "high": [101.0], "low": [99.0], "close": [100.0], "volume": [10.0]}
    )
    result = run_historical('//@version=5\nindicator("clock")\nnow = time\n', frame)
    assert math.isnan(result.final_state["now"])

"""백테스트 엔진에 넘긴 캔들 구간을 요청 구간과 구분한다."""

from datetime import datetime

import pandas as pd
from pydantic import AwareDatetime, BaseModel, Field

from src.market_data.constants import TIMEFRAME_SECONDS


class DataCoverage(BaseModel):
    actual_start: AwareDatetime | None
    actual_end: AwareDatetime | None
    bar_count: int = Field(ge=0)
    expected_bars: int = Field(ge=0)
    missing_bars: int = Field(ge=0)


def measure_data_coverage(
    index: pd.DatetimeIndex, timeframe: str, start: datetime, end: datetime
) -> DataCoverage:
    """UTC 캔들 개시 시각, 요청 양 끝 포함. 중간 누락도 센다."""
    frequency = f"{TIMEFRAME_SECONDS[timeframe]}s"
    expected = pd.date_range(
        pd.Timestamp(start).tz_convert("UTC").ceil(frequency),
        pd.Timestamp(end).tz_convert("UTC").floor(frequency),
        freq=frequency,
    )
    return DataCoverage(
        actual_start=index.min().to_pydatetime() if len(index) else None,
        actual_end=index.max().to_pydatetime() if len(index) else None,
        bar_count=len(index),
        expected_bars=len(expected),
        missing_bars=len(expected.difference(index)),
    )

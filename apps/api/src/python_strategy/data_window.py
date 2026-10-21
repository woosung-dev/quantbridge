"""요청한 봉과 펀딩이 실제로 존재할 때만 Python 실험을 실행한다."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pandas as pd


def complete_window(
    frame: pd.DataFrame, start: datetime, end: datetime, timeframe: str
) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError("OHLCV에는 UTC 시각 인덱스가 필요합니다.")
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError("OHLCV가 중복되었거나 시간순이 아닙니다.")
    start_ts, end_ts = pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")
    expected = pd.date_range(start_ts, end_ts, freq=timeframe, inclusive="left")
    window = frame[(frame.index >= start_ts) & (frame.index < end_ts)]
    if not window.index.equals(expected):
        raise ValueError(
            f"요청 기간 데이터가 부족합니다: 필요 {len(expected)}봉, 실제 {len(window)}봉."
        )
    columns = ["open", "high", "low", "close", "volume"]
    if not set(columns).issubset(window.columns):
        raise ValueError("OHLCV 열이 누락되었습니다.")
    for values in window[columns].itertuples(index=False, name=None):
        o, h, low, close, volume = (Decimal(str(item)) for item in values)
        if not all(item.is_finite() for item in (o, h, low, close, volume)):
            raise ValueError("OHLCV에 유한하지 않은 값이 있습니다.")
        if min(o, h, low, close) <= 0 or volume < 0 or low > min(o, close) or h < max(o, close):
            raise ValueError("OHLCV 가격·거래량 관계가 잘못되었습니다.")
    return window


def complete_funding(rates: pd.Series, start: datetime, end: datetime) -> pd.Series:
    # 첫 버전의 BTC·ETH USDT 계약은 UTC 00/08/16시 정산 자료를 요구한다.
    start_ts, end_ts = pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")
    expected = pd.date_range(start_ts.ceil("8h"), end_ts, freq="8h", inclusive="left")
    if not len(expected):
        return pd.Series(dtype=object, index=pd.DatetimeIndex([], tz="UTC"))
    if not isinstance(rates.index, pd.DatetimeIndex) or rates.index.tz is None:
        raise ValueError("펀딩 시각 자료가 없습니다.")
    if not rates.index.is_unique or not rates.index.is_monotonic_increasing:
        raise ValueError("펀딩 자료가 중복되었거나 시간순이 아닙니다.")
    selected = rates.loc[(rates.index >= start_ts) & (rates.index < end_ts)]
    if not selected.index.equals(expected):
        raise ValueError("요청 기간의 실제 펀딩 자료가 부족합니다. 펀딩 0으로 대체하지 않습니다.")
    if any(not Decimal(str(value)).is_finite() for value in selected):
        raise ValueError("펀딩 값이 유한하지 않습니다.")
    return selected

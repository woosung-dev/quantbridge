"""공개 원문 B 묶음의 독립 Python 계산. Pine 인터프리터를 호출하지 않는다."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from scripts.pine_validation.models import SignalEvent


def gann_high_low(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """XNQSLIYb: 이전 봉 nz(SMA)로 상태를 정하고 현재 SMA와 종가의 교차를 읽는다."""
    from scripts.pine_validation.oracles import (
        crossover,
        crossunder,
        events_from_conditions,
        sma,
        source_values,
    )

    close = source_values(ohlcv)
    high = sma(source_values(ohlcv, "high"), params.get("high_period", 13))
    low = sma(source_values(ohlcv, "low"), params.get("low_period", 21))
    line = np.full(len(close), np.nan)
    state = 0
    for index, price in enumerate(close):
        if index:
            previous_high = 0 if np.isnan(high[index - 1]) else high[index - 1]
            previous_low = 0 if np.isnan(low[index - 1]) else low[index - 1]
            direction = 1 if price > previous_high else -1 if price < previous_low else 0
            if direction:
                state = direction
        line[index] = high[index] if state == -1 else low[index]
    return events_from_conditions(ohlcv, crossover(close, line), crossunder(close, line))


def stochastic_kd(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """kVJIw2Ct 55/56: K/D 교차 위치의 K값 0은 plotshape의 불발이다."""
    from scripts.pine_validation.oracles import (
        _period,
        crossover,
        crossunder,
        events_from_conditions,
        sma,
        source_values,
    )

    length = _period(params.get("period_k", 14))
    high = ohlcv["high"].rolling(length, min_periods=1).max().to_numpy()
    low = ohlcv["low"].rolling(length, min_periods=1).min().to_numpy()
    denominator = high - low
    raw = np.divide(
        100 * (source_values(ohlcv, params.get("source", "close")) - low),
        denominator,
        out=np.full(len(ohlcv), np.nan),
        where=denominator != 0,
    )
    k = sma(raw, params.get("smooth_k", 3))
    d = sma(k, params.get("period_d", 3))
    enabled = params.get("highlight_crossovers", True)
    if type(enabled) is not bool:
        raise ValueError("highlight_crossovers는 bool이어야 합니다")
    visible = enabled & np.isfinite(k) & (k != 0)
    return events_from_conditions(ohlcv, crossover(k, d) & visible, crossunder(k, d) & visible)


def trend_magic(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """kRIjThLZ: CCI 부호·SMA(tr) trailing 상태와 low/high 교차를 보존한다."""
    from scripts.pine_validation.oracles import (
        _period,
        crossover,
        crossunder,
        events_from_conditions,
        sma,
        source_values,
    )

    source = source_values(ohlcv, params.get("source", "close"))
    length = _period(params.get("period", 20))
    center = sma(source, length)
    cci = np.full(len(source), np.nan)
    for index in range(length - 1, len(source)):
        deviation = np.mean(np.abs(source[index - length + 1 : index + 1] - center[index]))
        if deviation:
            cci[index] = (source[index] - center[index]) / (0.015 * deviation)
    high, low, close = (source_values(ohlcv, key) for key in ("high", "low", "close"))
    previous = np.roll(close, 1)
    if len(previous):
        previous[0] = np.nan
    # 원문 tr 변수는 첫 봉 NA이며 ta.tr(true)의 high-low fallback과 다르다.
    tr = np.maximum(high - low, np.maximum(abs(high - previous), abs(low - previous)))
    ranges = sma(tr, params.get("atr_period", 5)) * params.get("coefficient", 1)
    line = np.full(len(close), np.nan)
    for index in range(len(close)):
        old = line[index - 1] if index and np.isfinite(line[index - 1]) else 0
        up, down = low[index] - ranges[index], high[index] + ranges[index]
        line[index] = max(up, old) if cci[index] >= 0 else min(down, old)
    return events_from_conditions(ohlcv, crossover(low, line), crossunder(high, line))


def parabolic_sar_values(
    ohlcv: pd.DataFrame,
    start: float = 0.02,
    increment: float = 0.02,
    maximum: float = 0.2,
) -> np.ndarray:
    """Wilder SAR의 직전 극점·가속·반전·직전 두 봉 clamp를 순차 계산한다."""
    from scripts.pine_validation.oracles import source_values

    high, low, close = (source_values(ohlcv, key) for key in ("high", "low", "close"))
    output = np.full(len(close), np.nan)
    below, extreme, acceleration, value = False, np.nan, start, np.nan
    for index in range(1, len(close)):
        first = index == 1
        if first:
            below = close[index] > close[index - 1]
            extreme = high[index] if below else low[index]
            value = low[index - 1] if below else high[index - 1]
        value += acceleration * (extreme - value)
        if below and value > low[index]:
            below, first = False, True
            value, extreme, acceleration = max(high[index], extreme), low[index], start
        elif not below and value < high[index]:
            below, first = True, True
            value, extreme, acceleration = min(low[index], extreme), high[index], start
        if not first:
            if below and high[index] > extreme:
                extreme, acceleration = high[index], min(acceleration + increment, maximum)
            elif not below and low[index] < extreme:
                extreme, acceleration = low[index], min(acceleration + increment, maximum)
        if below:
            value = min(value, low[index - 1])
            if index > 1:
                value = min(value, low[index - 2])
        else:
            value = max(value, high[index - 1])
            if index > 1:
                value = max(value, high[index - 2])
        output[index] = value
    return output


def parabolic_sar(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """MddD4giy 45/46: SAR<close 방향 전환 alert만 읽고 화면 표식은 중복하지 않는다."""
    from scripts.pine_validation.oracles import events_from_conditions, source_values

    line = parabolic_sar_values(
        ohlcv, params.get("start", 0.02), params.get("increment", 0.02), params.get("maximum", 0.2)
    )
    direction = np.where(line < source_values(ohlcv), 1, -1)
    change = np.diff(direction, prepend=direction[0]) if len(direction) else direction
    return events_from_conditions(ohlcv, change > 0, change < 0)


ORACLES_B: dict[str, Callable[[pd.DataFrame, Mapping[str, Any]], list[SignalEvent]]] = {
    "gann_high_low": gann_high_low,
    "stochastic_kd": stochastic_kd,
    "trend_magic": trend_magic,
    "parabolic_sar": parabolic_sar,
}

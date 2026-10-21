"""C 묶음의 검토된 원문 신호 계산. Pine 인터프리터·stdlib를 재사용하지 않는다."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from scripts.pine_validation.models import SignalEvent


def rsi_signals_entries(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """MXaEHFCb 246/247: 각 RSI 구간 방문당 한 번 발화하는 confirmed-bar 알림."""
    from scripts.pine_validation.oracles import events_from_conditions, rsi, sma, source_values

    close, opening = source_values(ohlcv), source_values(ohlcv, "open")
    values = rsi(source_values(ohlcv, params.get("source", "close")), params.get("rsi_length", 14))
    over_buy, resistance = params.get("over_buy", 79.9), params.get("resistance", 67.9)
    support, over_sold = params.get("support", 34.9), params.get("over_sold", 19.9)
    bodies = abs(close - opening)
    average = sma(bodies, params.get("strong_lookback", 20))
    strong = bodies >= average * params.get("strong_multiplier", 1.2)
    zones = np.column_stack(
        (
            values >= over_buy,
            (values >= resistance) & (values < over_buy),
            (values <= support) & (values > over_sold),
            values <= over_sold,
        )
    )
    fired = np.zeros(4, dtype=bool)
    buy, sell = np.zeros(len(close), dtype=bool), np.zeros(len(close), dtype=bool)
    for index, occupied in enumerate(zones):
        fired[~occupied] = False
        allowed = np.array(
            [
                True,
                close[index] < opening[index] and strong[index],
                close[index] > opening[index] and strong[index],
                True,
            ]
        )
        signals = occupied & ~fired & allowed
        fired |= signals
        sell[index], buy[index] = signals[:2].any(), signals[2:].any()
    # 역사 확정봉은 confirmOnClose의 true/false 모두 barReady=true다.
    return events_from_conditions(ohlcv, buy.tolist(), sell.tolist())


def everget_supertrend_values(
    ohlcv: pd.DataFrame,
    atr_period: int = 22,
    factor: float = 3,
    source: str = "hl2",
    wicks: bool = True,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.int64]]:
    """VLWVV7tH의 양수 stop·4가격 doji·이전 wick 기준 trailing과 방향을 보존한다."""
    from scripts.pine_validation.oracles import atr, source_values

    if type(wicks) is not bool:
        raise ValueError("wicks는 bool이어야 합니다")
    close, opening, high, low = (
        source_values(ohlcv, key) for key in ("close", "open", "high", "low")
    )
    centers = source_values(ohlcv, source)
    ranges = factor * atr(ohlcv, atr_period)
    high_price, low_price = (high, low) if wicks else (close, close)
    lower, upper = np.full(len(close), np.nan), np.full(len(close), np.nan)
    directions = np.ones(len(close), dtype=int)
    direction = 1
    for index in range(len(close)):
        raw_lower, raw_upper = centers[index] - ranges[index], centers[index] + ranges[index]
        prev_lower = lower[index - 1] if index and not np.isnan(lower[index - 1]) else raw_lower
        prev_upper = upper[index - 1] if index and not np.isnan(upper[index - 1]) else raw_upper
        doji = opening[index] == close[index] == low[index] == high[index]
        lower[index] = raw_lower
        if not raw_lower > 0 or doji:
            lower[index] = prev_lower
        elif index and low_price[index - 1] > prev_lower:
            lower[index] = max(raw_lower, prev_lower)
        upper[index] = raw_upper
        if not raw_upper > 0 or doji:
            upper[index] = prev_upper
        elif index and high_price[index - 1] < prev_upper:
            upper[index] = min(raw_upper, prev_upper)
        if direction == -1 and high_price[index] > prev_upper:
            direction = 1
        elif direction == 1 and low_price[index] < prev_lower:
            direction = -1
        directions[index] = direction
    return lower, upper, directions


def everget_supertrend(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """77/78 방향 전환 alert를 읽으며 showLabels는 알림을 숨기지 않는다."""
    from scripts.pine_validation.oracles import events_from_conditions

    _, _, direction = everget_supertrend_values(
        ohlcv,
        params.get("atr_period", 22),
        params.get("factor", 3),
        params.get("source", "hl2"),
        params.get("wicks", True),
    )
    buy, sell = np.zeros(len(ohlcv), dtype=bool), np.zeros(len(ohlcv), dtype=bool)
    buy[1:] = (direction[1:] == 1) & (direction[:-1] == -1)
    sell[1:] = (direction[1:] == -1) & (direction[:-1] == 1)
    return events_from_conditions(ohlcv, buy.tolist(), sell.tolist())


def qqe_primary_zero_cross(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """TpUW4muw 93/94: Primary RSI→EMA의 50 교차. QQE 색칠 plot 조건과 별개다."""
    from scripts.pine_validation.oracles import (
        crossover,
        crossunder,
        ema,
        events_from_conditions,
        rsi,
        source_values,
    )

    values = ema(
        rsi(source_values(ohlcv, params.get("source", "close")), params.get("rsi_length", 6)),
        params.get("rsi_smoothing", 5),
    )
    return events_from_conditions(
        ohlcv, crossover(values, 50).tolist(), crossunder(values, 50).tolist()
    )


ORACLES_C: dict[str, Callable[[pd.DataFrame, Mapping[str, Any]], list[SignalEvent]]] = {
    "rsi_signals_entries": rsi_signals_entries,
    "everget_supertrend": everget_supertrend,
    "qqe_primary_zero_cross": qqe_primary_zero_cross,
}

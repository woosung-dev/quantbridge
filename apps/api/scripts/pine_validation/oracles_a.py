"""검토한 공개 Pine 두 원본의 독립 계산기. 인터프리터 코드는 사용하지 않는다."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from scripts.pine_validation.models import SignalEvent, utc_time


def _sma(values: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    for i in range(length - 1, len(values)):
        window = values[i - length + 1 : i + 1]
        if np.isfinite(window).all():
            result[i] = window.mean()
    return result


def _stdev(values: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    for i in range(length - 1, len(values)):
        window = values[i - length + 1 : i + 1]
        if np.isfinite(window).all():
            result[i] = window.std(ddof=0)
    return result


def _rma(values: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    seed: list[float] = []
    previous = np.nan
    for i, value in enumerate(values):
        if np.isfinite(value):
            if np.isnan(previous):
                seed.append(float(value))
                if len(seed) == length:
                    previous = sum(seed) / length
            else:
                previous = (previous * (length - 1) + value) / length
        result[i] = previous
    return result


def _rsi(values: np.ndarray, length: int) -> np.ndarray:
    changes = np.diff(values, prepend=np.nan)
    gains = _rma(np.maximum(changes, 0), length)
    losses = _rma(np.maximum(-changes, 0), length)
    result = np.full(len(values), np.nan)
    ready = np.isfinite(gains) & np.isfinite(losses)
    result[ready & (losses == 0)] = 100.0
    result[ready & (gains == 0) & (losses > 0)] = 0.0
    middle = ready & (gains > 0) & (losses > 0)
    result[middle] = 100 - 100 / (1 + gains[middle] / losses[middle])
    return result


def _cross(left: np.ndarray, right: np.ndarray | float, *, above: bool) -> np.ndarray:
    other = np.broadcast_to(np.asarray(right, dtype=float), left.shape)
    result = np.zeros(len(left), dtype=bool)
    if above:
        result[1:] = (left[1:] > other[1:]) & (left[:-1] <= other[:-1])
    else:
        result[1:] = (left[1:] < other[1:]) & (left[:-1] >= other[:-1])
    return result


def _atr(frame: pd.DataFrame, length: int) -> np.ndarray:
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    previous = np.concatenate(([np.nan], close[:-1]))
    ranges = np.maximum(high - low, np.maximum(abs(high - previous), abs(low - previous)))
    ranges[0] = high[0] - low[0]
    return _rma(ranges, length)


def _events(frame: pd.DataFrame, signals: Mapping[str, np.ndarray]) -> list[SignalEvent]:
    return [
        SignalEvent(utc_time(at), direction)  # type: ignore[arg-type]
        for i, at in enumerate(frame.index)
        for direction, active in signals.items()
        if active[i]
    ]


def atr_bollinger(frame: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """6Pc4XLwR L15-72: 지속 BB 상태, ATR 추적선, iTrend 전환."""
    close = frame["close"].to_numpy(dtype=float)
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    period = int(params.get("BBperiod", 21))
    deviation = float(params.get("BBdeviation", 1.0))
    center = _sma(close, period)
    spread = deviation * _stdev(close, period)
    atr = _atr(frame, int(params.get("ATRperiod", 5)))
    use_atr = bool(params.get("UseATRfilter", True))
    buy = np.zeros(len(frame), dtype=bool)
    sell = np.zeros(len(frame), dtype=bool)
    bb_signal = trend = 0
    elite = np.nan
    for i, price in enumerate(close):
        if price > center[i] + spread[i]:
            bb_signal = 1
        elif price < center[i] - spread[i]:
            bb_signal = -1
        previous_elite = elite
        if bb_signal == 1:
            elite = low[i] - atr[i] if use_atr else low[i]
            if elite < (0 if np.isnan(previous_elite) else previous_elite):
                elite = 0 if np.isnan(previous_elite) else previous_elite
        elif bb_signal == -1:
            elite = high[i] + atr[i] if use_atr else high[i]
            if elite > (0 if np.isnan(previous_elite) else previous_elite):
                elite = 0 if np.isnan(previous_elite) else previous_elite
        previous_trend = trend
        now = 0 if np.isnan(elite) else elite
        before = 0 if np.isnan(previous_elite) else previous_elite
        if now > before:
            trend = 1
        elif now < before:
            trend = -1
        buy[i] = previous_trend == -1 and trend == 1
        sell[i] = previous_trend == 1 and trend == -1
    return _events(frame, {"long": buy, "short": sell})


def rsi_bollinger_long_short(frame: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    """5VupZDbT L29-77: RSI·밴드 교차와 마지막 매수/매도 가격 게이트."""
    source = str(params.get("src", "close"))
    if source not in {"open", "high", "low", "close"}:
        raise ValueError("오라클은 검토한 OHLC source만 허용합니다")
    values = frame[source].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    bb_length = int(params.get("bbLen", 20))
    basis = _sma(values, bb_length)
    spread = float(params.get("bbMult", 2.0)) * _stdev(values, bb_length)
    upper, lower = basis + spread, basis - spread
    rsi = _rsi(values, int(params.get("rsiLen", 14)))
    buy_raw = _cross(rsi, float(params.get("rsiBuyLevel", 29.0)), above=True)
    short_raw = _cross(rsi, float(params.get("rsiSellLevel", 71.0)), above=False)
    long_exit = _cross(values, upper, above=False)
    short_exit = _cross(values, lower, above=True)
    buy = np.zeros(len(frame), dtype=bool)
    short = np.zeros(len(frame), dtype=bool)
    last_buy = last_short = np.nan
    drop = float(params.get("dropPct", 5.0)) / 100
    rise = float(params.get("risePct", 5.0)) / 100
    for i, price in enumerate(close):
        buy[i] = buy_raw[i] and (np.isnan(last_buy) or price <= last_buy * (1 - drop))
        short[i] = short_raw[i] and (np.isnan(last_short) or price >= last_short * (1 + rise))
        if long_exit[i]:
            last_buy = np.nan
        elif buy[i]:
            last_buy = price
        if short_exit[i]:
            last_short = np.nan
        elif short[i]:
            last_short = price
    return _events(
        frame,
        {"long": buy, "long_exit": long_exit, "short": short, "short_exit": short_exit},
    )


ORACLES_A: dict[str, Callable[[pd.DataFrame, Mapping[str, Any]], list[SignalEvent]]] = {
    "atr_bollinger": atr_bollinger,
    "rsi_bollinger_long_short": rsi_bollinger_long_short,
}

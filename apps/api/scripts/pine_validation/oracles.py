"""검토 가능한 로컬 Python 계산기. Pine 실행 코드와 구현을 공유하지 않는다.

아래 템플릿 이름만으로 TradingView 지표와의 동등성을 주장할 수 없다. 수집 manifest가
원본 hash·신호 조건·파라미터를 이 구현에 명시적으로 연결해야 실제 검증 대상으로 삼는다.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from scripts.pine_validation.models import SignalEvent, utc_time

Values = Sequence[float] | pd.Series | np.ndarray


def _period(length: int) -> int:
    if isinstance(length, bool) or int(length) != length or length < 1:
        raise ValueError("지표 기간은 양의 정수여야 합니다")
    return int(length)


def sma(source: Values, length: int) -> np.ndarray:
    """최근 length개 비NA 표본의 평균. 초기 표본이 모자라면 NA다."""
    length = _period(length)
    output = np.full(len(source), np.nan)
    samples: deque[float] = deque()
    total = 0.0
    for index, value in enumerate(np.asarray(source, dtype=float)):
        if not np.isnan(value):
            samples.append(float(value))
            total += float(value)
            if len(samples) > length:
                total -= samples.popleft()
        if len(samples) == length:
            output[index] = total / length
    return output


def ema(source: Values, length: int) -> np.ndarray:
    """첫 비NA 표본으로 seed한다. pandas의 기본 warmup을 사용하지 않는다."""
    length = _period(length)
    alpha, previous = 2.0 / (length + 1), np.nan
    output = np.full(len(source), np.nan)
    for index, value in enumerate(np.asarray(source, dtype=float)):
        if not np.isnan(value):
            previous = (
                float(value) if np.isnan(previous) else alpha * value + (1 - alpha) * previous
            )
        output[index] = previous
    return output


def rma(source: Values, length: int) -> np.ndarray:
    """Wilder RMA: 비NA length개 SMA seed 뒤 alpha=1/length다."""
    length = _period(length)
    output = np.full(len(source), np.nan)
    seed: list[float] = []
    previous = np.nan
    for index, value in enumerate(np.asarray(source, dtype=float)):
        if not np.isnan(value):
            if np.isnan(previous):
                seed.append(float(value))
                if len(seed) == length:
                    previous = sum(seed) / length
            else:
                previous = (previous * (length - 1) + value) / length
        output[index] = previous
    return output


def rsi(source: Values, length: int = 14) -> np.ndarray:
    """변화량의 상승·하락 RMA로 RSI를 계산한다. 첫 변화량은 NA다."""
    values = np.asarray(source, dtype=float)
    changes = np.diff(values, prepend=np.nan)
    up, down = rma(np.maximum(changes, 0), length), rma(np.maximum(-changes, 0), length)
    output = np.full(len(values), np.nan)
    for index, (gain, loss) in enumerate(zip(up, down, strict=True)):
        if np.isnan(gain) or np.isnan(loss):
            continue
        output[index] = 100.0 if loss == 0 else 0.0 if gain == 0 else 100 - 100 / (1 + gain / loss)
    return output


def crossover(left: Values, right: Values | float) -> np.ndarray:
    a = np.asarray(left, dtype=float)
    b = np.broadcast_to(np.asarray(right, dtype=float), a.shape)
    output = np.zeros(len(a), dtype=bool)
    output[1:] = (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    return output


def crossunder(left: Values, right: Values | float) -> np.ndarray:
    return crossover(-np.asarray(left, dtype=float), -np.asarray(right, dtype=float))


def true_range(ohlcv: pd.DataFrame) -> np.ndarray:
    """직전 종가가 NA인 봉은 high-low로 시작한다(ta.tr(true))."""
    high, low, close = (ohlcv[column].to_numpy(dtype=float) for column in ("high", "low", "close"))
    previous = np.roll(close, 1)
    if len(previous):
        previous[0] = np.nan
    return np.where(
        np.isnan(previous),
        high - low,
        np.maximum(high - low, np.maximum(abs(high - previous), abs(low - previous))),
    )


def atr(ohlcv: pd.DataFrame, length: int = 14) -> np.ndarray:
    return rma(true_range(ohlcv), length)


def supertrend(
    ohlcv: pd.DataFrame, factor: float = 3, atr_period: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """hl2·Wilder ATR의 표준 supertrend. 방향 -1=상승, +1=하락이다."""
    close = ohlcv["close"].to_numpy(dtype=float)
    midpoint = (ohlcv["high"].to_numpy(dtype=float) + ohlcv["low"].to_numpy(dtype=float)) / 2
    ranges = atr(ohlcv, atr_period)
    output, direction = np.full(len(close), np.nan), np.ones(len(close), dtype=int)
    previous_lower = previous_upper = previous_line = np.nan
    for index, price in enumerate(close):
        if np.isnan(ranges[index]):
            previous_lower = previous_upper = previous_line = np.nan
            continue
        lower, upper = (
            midpoint[index] - factor * ranges[index],
            midpoint[index] + factor * ranges[index],
        )
        if index and not np.isnan(previous_lower):
            lower = (
                lower
                if lower > previous_lower or close[index - 1] < previous_lower
                else previous_lower
            )
            upper = (
                upper
                if upper < previous_upper or close[index - 1] > previous_upper
                else previous_upper
            )
        if index == 0 or np.isnan(ranges[index - 1]):
            direction[index] = 1
        elif previous_line == previous_upper:
            direction[index] = -1 if price > upper else 1
        else:
            direction[index] = 1 if price < lower else -1
        output[index] = lower if direction[index] == -1 else upper
        previous_lower, previous_upper, previous_line = lower, upper, output[index]
    return output, direction


def source_values(ohlcv: pd.DataFrame, name: str = "close") -> np.ndarray:
    if name in ("open", "high", "low", "close"):
        return ohlcv[name].to_numpy(dtype=float)
    fields = {
        "hl2": ("high", "low"),
        "hlc3": ("high", "low", "close"),
        "ohlc4": ("open", "high", "low", "close"),
    }
    if name not in fields:
        raise ValueError(f"지원하지 않는 oracle source: {name}")
    return ohlcv[list(fields[name])].to_numpy(dtype=float).mean(axis=1)


def utbot(
    ohlcv: pd.DataFrame, key_value: float = 1, atr_period: int = 10, source: str = "close"
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """UT Bot의 ATR trailing stop와 EMA(1) 교차 조건을 독립 계산한다."""
    prices = source_values(ohlcv, source)
    loss = key_value * atr(ohlcv, atr_period)
    stop = np.full(len(prices), np.nan)
    for index, price in enumerate(prices):
        previous = stop[index - 1] if index and not np.isnan(stop[index - 1]) else 0.0
        previous_price = prices[index - 1] if index else np.nan
        if price > previous and previous_price > previous:
            stop[index] = np.maximum(previous, price - loss[index])
        elif price < previous and previous_price < previous:
            stop[index] = np.minimum(previous, price + loss[index])
        else:
            stop[index] = price - loss[index] if price > previous else price + loss[index]
    fast = ema(prices, 1)
    return stop, (prices > stop) & crossover(fast, stop), (prices < stop) & crossover(stop, fast)


def kivanc_supertrend(
    ohlcv: pd.DataFrame,
    factor: float = 3,
    atr_period: int = 10,
    source: str = "hl2",
    atr_method: str = "rma",
    ignore_wicks: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Kivanc 원본의 상승 seed·이전 밴드 전환. ta.supertrend의 하락 seed와 다르다."""
    if atr_method not in {"rma", "sma"}:
        raise ValueError("Kivanc ATR 방식은 rma 또는 sma여야 합니다")
    ranges = (rma if atr_method == "rma" else sma)(true_range(ohlcv), atr_period)
    centers = source_values(ohlcv, source)
    close, high, low = (ohlcv[name].to_numpy(dtype=float) for name in ("close", "high", "low"))
    lower, upper = np.full(len(close), np.nan), np.full(len(close), np.nan)
    trend = np.ones(len(close), dtype=int)
    for index, price in enumerate(close):
        raw_lower, raw_upper = (
            centers[index] - factor * ranges[index],
            centers[index] + factor * ranges[index],
        )
        previous_lower = lower[index - 1] if index and not np.isnan(lower[index - 1]) else raw_lower
        previous_upper = upper[index - 1] if index and not np.isnan(upper[index - 1]) else raw_upper
        previous_close = close[index - 1] if index else np.nan
        lower[index] = (
            max(raw_lower, previous_lower) if previous_close > previous_lower else raw_lower
        )
        upper[index] = (
            min(raw_upper, previous_upper) if previous_close < previous_upper else raw_upper
        )
        previous_trend = trend[index - 1] if index else 1
        if previous_trend == -1 and (price if ignore_wicks else high[index]) > previous_upper:
            trend[index] = 1
        elif previous_trend == 1 and (price if ignore_wicks else low[index]) < previous_lower:
            trend[index] = -1
        else:
            trend[index] = previous_trend
    return np.where(trend == 1, lower, upper), trend


def events_from_conditions(
    ohlcv: pd.DataFrame, buy: Sequence[bool], sell: Sequence[bool]
) -> list[SignalEvent]:
    if len(ohlcv) != len(buy) or len(ohlcv) != len(sell):
        raise ValueError("봉수와 신호 조건 길이가 다릅니다")
    output = []
    for index, at in enumerate(ohlcv.index):
        for direction, active in (("long", buy[index]), ("short", sell[index])):
            if active is not None and not pd.isna(active) and active:
                output.append(SignalEvent(utc_time(at), direction))  # type: ignore[arg-type]
    return output


def _moving_average_cross(
    ohlcv: pd.DataFrame, params: Mapping[str, Any], average: Callable[[Values, int], np.ndarray]
) -> list[SignalEvent]:
    values = source_values(ohlcv, params.get("source", "close"))
    fast, slow = average(values, params.get("fast", 9)), average(values, params.get("slow", 21))
    return events_from_conditions(ohlcv, crossover(fast, slow), crossunder(fast, slow))


def ema_cross(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    return _moving_average_cross(ohlcv, params, ema)


def sma_cross(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    return _moving_average_cross(ohlcv, params, sma)


def rsi_threshold(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    values = rsi(source_values(ohlcv, params.get("source", "close")), params.get("length", 14))
    return events_from_conditions(
        ohlcv,
        crossover(values, params.get("lower", 30)),
        crossunder(values, params.get("upper", 70)),
    )


def supertrend_signals(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    _, direction = supertrend(ohlcv, params.get("factor", 3), params.get("atr_period", 10))
    changes = np.diff(direction, prepend=direction[0]) if len(direction) else direction
    return events_from_conditions(ohlcv, changes < 0, changes > 0)


def utbot_signals(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    _, buy, sell = utbot(
        ohlcv,
        params.get("key_value", 1),
        params.get("atr_period", 10),
        params.get("source", "close"),
    )
    return events_from_conditions(ohlcv, buy, sell)


def kivanc_supertrend_signals(ohlcv: pd.DataFrame, params: Mapping[str, Any]) -> list[SignalEvent]:
    _, trend = kivanc_supertrend(
        ohlcv,
        params.get("factor", 3),
        params.get("atr_period", 10),
        params.get("source", "hl2"),
        params.get("atr_method", "rma"),
        params.get("ignore_wicks", True),
    )
    changes = np.diff(trend, prepend=trend[0]) if len(trend) else trend
    return events_from_conditions(ohlcv, changes > 0, changes < 0)


ORACLES: dict[str, Callable[[pd.DataFrame, Mapping[str, Any]], list[SignalEvent]]] = {
    "ema_cross": ema_cross,
    "sma_cross": sma_cross,
    "rsi_threshold": rsi_threshold,
    "supertrend": supertrend_signals,
    "utbot": utbot_signals,
    "kivanc_supertrend": kivanc_supertrend_signals,
}


def compute_oracle(
    name: str, ohlcv: pd.DataFrame, params: Mapping[str, Any] | None = None
) -> list[SignalEvent]:
    if not isinstance(ohlcv.index, pd.DatetimeIndex) or ohlcv.index.tz is None:
        raise ValueError("oracle OHLCV에는 시간대가 있는 DatetimeIndex가 필요합니다")
    if not ohlcv.index.is_monotonic_increasing or ohlcv.index.has_duplicates:
        raise ValueError("oracle OHLCV 봉은 중복 없이 시간순이어야 합니다")
    if name not in ORACLES:
        raise ValueError(f"검토한 Python oracle이 없습니다: {name}")
    params = params or {}
    events = ORACLES[name](ohlcv, params)
    if not events:
        return events
    differences = ohlcv.index.to_series().diff().dropna().unique()
    if len(differences) != 1:
        raise ValueError("oracle 확정 시각에는 일정한 봉 간격이 필요합니다")
    step = pd.Timedelta(differences[0]).to_pytimedelta()
    offsets = params.get("marker_offsets", {})
    result = []
    for event in events:
        offset = offsets.get(event.direction, params.get("marker_offset", 0))
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise ValueError("oracle 표시 오프셋은 정수 봉수여야 합니다")
        result.append(
            replace(
                event,
                confirmed_at=event.confirmed_at
                if event.confirmed_at is not None
                else event.bar_time + step,
                display_time=event.display_time
                if event.display_time is not None
                else event.bar_time + step * offset,
            )
        )
    return result

"""Pine 내장 함수 화이트리스트 + 참조 구현.

각 함수는 pandas Series를 입력받고 반환. pandas-ta / pandas / numpy 위임으로
TradingView 재현성 확보.

스프린트 1 범위: EMA Cross / SuperTrend 수준 전략을 돌릴 최소 셋.
Phase A 결과에 따라 함수 추가.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


def _ta_sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).mean()


def _ta_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=int(length), adjust=False).mean()


def _ta_rma(series: pd.Series, length: int) -> pd.Series:
    # Wilder's smoothing = EMA with alpha = 1/length
    return series.ewm(alpha=1.0 / int(length), adjust=False).mean()


def _ta_rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    avg_up = _ta_rma(up, length)
    avg_down = _ta_rma(down, length)
    rs = avg_up / avg_down.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(100.0)  # down=0인 경우 RSI=100


def _ta_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _ta_rma(tr, length)


def _ta_stdev(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).std(ddof=0)


def _ta_crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    prev_a = a.shift(1)
    prev_b = b.shift(1)
    return (a > b) & (prev_a <= prev_b)


def _ta_crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    prev_a = a.shift(1)
    prev_b = b.shift(1)
    return (a < b) & (prev_a >= prev_b)


def _ta_cross(a: pd.Series, b: pd.Series) -> pd.Series:
    return _ta_crossover(a, b) | _ta_crossunder(a, b)


def _ta_highest(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).max()


def _ta_lowest(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).min()


def _ta_change(series: pd.Series, length: int = 1) -> pd.Series:
    return series.diff(int(length))


def _nz(series: pd.Series, replacement: float = 0.0) -> pd.Series:
    return series.fillna(replacement)


def _na(series: pd.Series) -> pd.Series:
    return series.isna()


SUPPORTED: dict[str, Callable[..., Any]] = {
    "ta.sma": _ta_sma,
    "ta.ema": _ta_ema,
    "ta.rma": _ta_rma,
    "ta.rsi": _ta_rsi,
    "ta.atr": _ta_atr,
    "ta.stdev": _ta_stdev,
    "ta.crossover": _ta_crossover,
    "ta.crossunder": _ta_crossunder,
    "ta.cross": _ta_cross,
    "ta.highest": _ta_highest,
    "ta.lowest": _ta_lowest,
    "ta.change": _ta_change,
    "nz": _nz,
    "na": _na,
}


def is_supported(name: str) -> bool:
    return name in SUPPORTED


def call_supported(name: str, *args: Any, **kwargs: Any) -> Any:
    if name not in SUPPORTED:
        raise KeyError(f"unsupported function: {name}")
    return SUPPORTED[name](*args, **kwargs)

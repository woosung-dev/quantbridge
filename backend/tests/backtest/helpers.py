"""백테스트/스트레스 테스트 공용 OHLCV fixture helper.

DB 의존 없이 pure pandas/numpy 로 결정적(sine/trending) OHLCV 를 생성한다.
`run_backtest` (pine_v2) + `run_walk_forward` 단위 테스트의 합성 시계열 공급용.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Pine 소스 — 단순 결정적 전략 (교차 기반 / crossover-less 둘 다)
# --------------------------------------------------------------------------

# 간단한 EMA crossover 전략 — 표준 run_backtest 경로에서 "ok" 가 나오는 최소 Pine.
SIMPLE_PINE = """//@version=5
strategy("WF Simple", overlay=true)
ema_fast = ta.ema(close, 5)
ema_slow = ta.ema(close, 20)
if ta.crossover(ema_fast, ema_slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(ema_fast, ema_slow)
    strategy.close("L")
"""

# "Overfit-prone" 전략 — 실상 SIMPLE_PINE 과 동일한 shape 이나 구분을 위해 별도 상수로 노출.
# 엔진 레벨에선 동일한 결과를 내지만 WalkForward 타입/플로우 테스트엔 충분.
OVERFIT_PINE = SIMPLE_PINE


# --------------------------------------------------------------------------
# 합성 OHLCV 제너레이터 — DatetimeIndex tz-aware UTC, 1h 간격.
# --------------------------------------------------------------------------


def make_sine_ohlcv(
    n_bars: int = 500,
    *,
    base: float = 100.0,
    amplitude: float = 5.0,
    period: int = 50,
    start: str = "2024-01-01",
    freq: str = "1h",
) -> pd.DataFrame:
    """결정적 sine wave OHLCV.

    - close = base + amplitude * sin(2π * i / period)
    - open = close[i-1] (첫 bar 는 close[0])
    - high = max(open, close) + 0.5 * amplitude / period
    - low  = min(open, close) - 0.5 * amplitude / period
    - volume = 100.0 (상수)
    - index = tz-aware UTC DatetimeIndex
    """
    idx = pd.date_range(start, periods=n_bars, freq=freq, tz="UTC")
    t = np.arange(n_bars)
    close = base + amplitude * np.sin(2 * np.pi * t / period)
    open_ = np.concatenate([[close[0]], close[:-1]])
    margin = 0.5 * amplitude / period
    high = np.maximum(open_, close) + margin
    low = np.minimum(open_, close) - margin
    volume = np.full(n_bars, 100.0)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


def make_trending_ohlcv(
    n_bars: int = 400,
    *,
    base: float = 100.0,
    drift_per_bar: float = 0.05,
    noise_amplitude: float = 1.0,
    noise_period: int = 20,
    start: str = "2024-01-01",
    freq: str = "1h",
) -> pd.DataFrame:
    """결정적 상승 추세 + 사인 노이즈 OHLCV."""
    idx = pd.date_range(start, periods=n_bars, freq=freq, tz="UTC")
    t = np.arange(n_bars)
    close = base + drift_per_bar * t + noise_amplitude * np.sin(2 * np.pi * t / noise_period)
    open_ = np.concatenate([[close[0]], close[:-1]])
    margin = 0.1 * noise_amplitude
    high = np.maximum(open_, close) + margin
    low = np.minimum(open_, close) - margin
    volume = np.full(n_bars, 100.0)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )

"""Sprint 25 BL-112 — backtest 통합 테스트용 결정적 OHLCV fixture.

codex G.0 iter 2 가 plan v2 의 "기존 fixture 재사용" 가설을 코드 실측으로 refute
했다 (`test_run_backtest.py:_ohlcv()` 30 bars + EMA cross → num_trades=0). 본 모듈이
`run_backtest_v2` 통합 테스트 용 신규 fixture (test internals import 금지).

`make_trending_ohlcv` 의 OHLCV 패턴 (8 segments × 25 bars = 200 bars 총) 은
EMA(3)/EMA(8) cross 가 정확히 3 회 발생하도록 설계됨 — `test_backtest_ohlcv_precondition`
이 매 build 시 이를 GREEN 으로 검증. trade count 가 변동하면 (vectorbt engine
업데이트 등) 본 fixture 의 segment 패턴을 조정.

사용처:
- `tests/integration/test_auto_dogfood.py:test_scenario2_backtest_engine_smoke`
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Sprint 25 BL-112 — EMA(3)/EMA(8) cross 결정적 trade 발생 보장.
# 8 segments alternation: 10 → 25 → 12 → 28 → 14 → 30 → 16 → 32
# 코드 실측 (Sprint 25 Phase 3): num_trades=3
EMA_CROSS_PINE_SOURCE = """//@version=5
strategy("EMA Cross Dogfood", overlay=true)
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""


def make_trending_ohlcv(n_bars: int = 200) -> pd.DataFrame:
    """8-segment alternating linspace (각 25 bars) → EMA cross 3 회 발생 보장.

    Parameters
    ----------
    n_bars : int
        반환 bar 수 (default 200, segment 8 × 25). 작아지면 cross 감소.

    Returns
    -------
    pd.DataFrame
        columns: open / high / low / close / volume. close 만 segment 패턴,
        OHLC 는 close ± 0.1~0.5 spread (단순 noise).
    """
    targets = [10.0, 25.0, 12.0, 28.0, 14.0, 30.0, 16.0, 32.0]
    segments: list[np.ndarray] = []
    prev = 10.0
    for tgt in targets:
        segments.append(np.linspace(prev, tgt, 25))
        prev = tgt
    close = np.concatenate(segments)[:n_bars]
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": [100.0] * len(close),
        }
    )

"""Sprint 8c — i3_drfx의 supertrend() multi-return 검증.

i3_drfx 전체는 30+ user function + request.security + alertcondition 다수로 H1 완주
목표 밖. 이 테스트는 supertrend() 함수 정의 + 호출만 isolated run으로 검증해서
user function core + multi-return tuple unpack이 실제 전략 함수에 동작함을 보장.
"""
from __future__ import annotations

import math as _math

import numpy as np
import pandas as pd

from src.strategy.pine_v2 import parse_and_run_v2

SUPERTREND_ISOLATED = '''
indicator("T", overlay=true)
supertrend(_close, factor, atrLen) =>
    atr = ta.atr(atrLen)
    upperBand = _close + factor * atr
    lowerBand = _close - factor * atr
    prevLowerBand = nz(lowerBand[1])
    prevUpperBand = nz(upperBand[1])
    lowerBand := lowerBand > prevLowerBand or close[1] < prevLowerBand ? lowerBand : prevLowerBand
    upperBand := upperBand < prevUpperBand or close[1] > prevUpperBand ? upperBand : prevUpperBand
    int direction = na
    float superTrend = na
    prevSuperTrend = superTrend[1]
    if na(atr[1])
        direction := 1
    else if prevSuperTrend == prevUpperBand
        direction := close > upperBand ? -1 : 1
    else
        direction := close < lowerBand ? 1 : -1
    superTrend := direction == -1 ? lowerBand : upperBand
    [superTrend, direction]

[st, dir] = supertrend(close, 3.0, 14)
'''


def _ohlcv(n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0, 1, n))
    high = close + 0.5
    low = close - 0.5
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": np.full(n, 100.0),
    })


def test_supertrend_returns_tuple_and_binds_both_locals() -> None:
    result = parse_and_run_v2(SUPERTREND_ISOLATED, _ohlcv(), strict=True)
    # Track M(indicator, no alert) → historical 결과에 var_series 포함
    assert result.track == "M"
    assert result.historical is not None
    vs = result.historical.var_series
    st_series = vs.get("st", [])
    dir_series = vs.get("dir", [])
    assert len(st_series) == 50
    assert len(dir_series) == 50
    # Sprint 8c MVP scope: user function body 내부 로컬 변수 subscript(atr[1],
    # superTrend[1])는 H2+ (local history ring 미지원). 따라서 direction은 항상 1 또는
    # -1로 계산되지만 값 자체의 정확도는 검증하지 않고, tuple unpack이 정상 작동했는지만
    # 확인한다.
    assert dir_series[-1] in (-1, 1), f"direction 예상 범위 밖: {dir_series[-1]}"
    # superTrend는 lowerBand/upperBand 중 하나 → finite float여야 함.
    assert not _math.isnan(st_series[-1]), (
        "superTrend 마지막 값 nan — tuple unpack 실패 또는 user function 반환 누락"
    )

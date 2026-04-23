"""Wilder RMA (ta.rma) unit tests — Sprint X1+X3 follow-up.

ta.rma(source, length) = Running Moving Average (Wilder smoothing).
- 첫 length 개 bar 는 SMA seed
- 이후 (prev * (length-1) + source) / length
- alpha = 1/length 의 EMA
"""
from __future__ import annotations

import math

from src.strategy.pine_v2.stdlib import IndicatorState, ta_rma


def test_ta_rma_warmup_returns_nan_until_seed() -> None:
    """warmup 단계 (length 미만) 는 nan, length 도달 시 SMA seed."""
    state = IndicatorState()
    results = []
    for src in [10.0, 20.0, 30.0]:
        results.append(ta_rma(state, 1, src, 3))
    # bar 1, 2: warmup (nan), bar 3: SMA seed = 60/3 = 20
    assert math.isnan(results[0])
    assert math.isnan(results[1])
    assert results[2] == 20.0


def test_ta_rma_wilder_smoothing_after_seed() -> None:
    """seed 후 (prev * (length-1) + source) / length."""
    state = IndicatorState()
    # length=3, seed = SMA(10,20,30) = 20
    for src in [10.0, 20.0, 30.0]:
        ta_rma(state, 1, src, 3)
    # bar 4: src=40 → rma = (20 * 2 + 40) / 3 = 80/3 ≈ 26.667
    bar4 = ta_rma(state, 1, 40.0, 3)
    assert abs(bar4 - 80.0 / 3.0) < 1e-9
    # bar 5: src=50 → rma = (26.667 * 2 + 50) / 3 ≈ 34.444
    bar5 = ta_rma(state, 1, 50.0, 3)
    assert abs(bar5 - (bar4 * 2 + 50.0) / 3.0) < 1e-9


def test_ta_rma_invalid_length_returns_nan() -> None:
    state = IndicatorState()
    assert math.isnan(ta_rma(state, 1, 10.0, 0))
    assert math.isnan(ta_rma(state, 2, 10.0, -1))


def test_ta_rma_nan_source_returns_prev() -> None:
    """source 가 nan 이면 직전 RMA 값 유지."""
    state = IndicatorState()
    for src in [10.0, 20.0, 30.0]:
        ta_rma(state, 1, src, 3)
    # nan 입력 → prev (=20) 반환
    result = ta_rma(state, 1, math.nan, 3)
    assert result == 20.0


def test_ta_rma_node_isolation() -> None:
    """다른 node_id 는 독립된 state."""
    state = IndicatorState()
    for src in [10.0, 20.0, 30.0]:
        ta_rma(state, 1, src, 3)
    # node 2 는 별도 — warmup 부터
    result = ta_rma(state, 2, 100.0, 3)
    assert math.isnan(result)

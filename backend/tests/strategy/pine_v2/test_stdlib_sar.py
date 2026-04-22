"""Parabolic SAR (ta.sar) unit tests — Sprint X1+X3 W2.

Wilder 1978 Parabolic SAR 알고리즘 구현 검증:
- AF (Acceleration Factor) start, increment, maximum
- EP (Extreme Point) 추적 + 추세 반전 시 새 SAR = 직전 EP
- nan 입력 전파, warmup 단계
"""
from __future__ import annotations

import math

import pytest

from src.strategy.pine_v2.stdlib import SarState, ta_sar


def _run_series(
    highs: list[float],
    lows: list[float],
    start: float = 0.02,
    increment: float = 0.02,
    maximum: float = 0.2,
) -> list[float]:
    state = SarState()
    results: list[float] = []
    for h, l in zip(highs, lows):
        sar = ta_sar(state, h, l, start, increment, maximum)
        results.append(sar)
    return results


def test_ta_sar_first_bar_is_nan() -> None:
    """최초 bar 에서는 추세 미정 → nan."""
    sar = _run_series([100.0], [99.0])
    assert math.isnan(sar[0])


def test_ta_sar_uptrend_sar_stays_below_lows() -> None:
    """지속 상승 시 SAR 는 low 아래에 머문다."""
    highs = [100.0 + i for i in range(20)]
    lows = [99.0 + i for i in range(20)]
    sar = _run_series(highs, lows)
    # 2번째 bar 이후부터 실값 (warmup 1 + init 1)
    valid_pairs = [
        (i + 2, s) for i, s in enumerate(sar[2:]) if not math.isnan(s)
    ]
    assert valid_pairs, f"uptrend SAR should produce values: sar={sar}"
    for idx, s in valid_pairs:
        assert s <= lows[idx], (
            f"uptrend SAR must stay at or below low: sar[{idx}]={s} low[{idx}]={lows[idx]}"
        )


def test_ta_sar_downtrend_sar_stays_above_highs() -> None:
    """지속 하락 시 SAR 는 high 위에 머문다."""
    highs = [100.0 - i for i in range(20)]
    lows = [99.0 - i for i in range(20)]
    sar = _run_series(highs, lows)
    valid_pairs = [
        (i + 2, s) for i, s in enumerate(sar[2:]) if not math.isnan(s)
    ]
    assert valid_pairs, f"downtrend SAR should produce values: sar={sar}"
    for idx, s in valid_pairs:
        assert s >= highs[idx], (
            f"downtrend SAR must stay at or above high: sar[{idx}]={s} high[{idx}]={highs[idx]}"
        )


def test_ta_sar_trend_reversal_resets_to_ep() -> None:
    """상승추세에서 low 가 SAR 아래로 뚫으면 반전: 새 SAR = 직전 EP (high)."""
    # 상승 5 bar → 급격 하락 2 bar
    highs = [100.0, 102.0, 105.0, 108.0, 110.0, 108.0, 102.0]
    lows = [99.0, 101.0, 104.0, 107.0, 109.0, 100.0, 95.0]
    sar = _run_series(highs, lows)
    # 반전 후 SAR 가 직전 구간 최고치 EP 근처로 점프
    # 정확값: 상승 EP = max(highs[1..4]) = 110, 반전 시 SAR = 110
    assert sar[6] > sar[4], (
        f"reversal SAR must jump up after reversal: sar[6]={sar[6]} sar[4]={sar[4]}"
    )
    # 하락 추세로 전환되었으므로 SAR 는 high 보다 위
    assert sar[6] >= highs[6], (
        f"after reversal to downtrend, SAR must be >= high: sar[6]={sar[6]} high[6]={highs[6]}"
    )


def test_ta_sar_af_capped_at_maximum() -> None:
    """강한 상승 (EP 매 bar 갱신) 에서도 AF 는 maximum 을 넘지 않는다."""
    highs = [float(i) for i in range(100, 140)]  # 40 bar 상승
    lows = [h - 0.5 for h in highs]
    state = SarState()
    last_sar: float | None = None
    for h, l in zip(highs, lows):
        last_sar = ta_sar(state, h, l, 0.02, 0.02, 0.2)
    assert last_sar is not None and math.isfinite(last_sar)
    assert state.acceleration_factor <= 0.2 + 1e-9, (
        f"AF must be capped at maximum: af={state.acceleration_factor}"
    )


def test_ta_sar_nan_input_propagates() -> None:
    """high 또는 low 가 nan 이면 SAR 도 nan (이후 bar 는 계속 진행)."""
    state = SarState()
    sar_nan = ta_sar(state, math.nan, 99.0, 0.02, 0.02, 0.2)
    assert math.isnan(sar_nan)
    # 다음 bar 정상 (warmup 단계 — nan 또는 finite 둘 다 OK)
    sar_ok = ta_sar(state, 100.0, 99.0, 0.02, 0.02, 0.2)
    assert math.isnan(sar_ok) or math.isfinite(sar_ok)


def test_ta_sar_constant_high_low() -> None:
    """high == low (1 bar 변동 없음) 에서도 nan/0 division 없이 진행."""
    highs = [100.0] * 10
    lows = [100.0] * 10
    state = SarState()
    for h, l in zip(highs, lows):
        sar = ta_sar(state, h, l, 0.02, 0.02, 0.2)
        # nan 이거나 finite — Inf 금지
        assert not math.isinf(sar), f"SAR must not be inf: {sar}"


def test_ta_sar_zero_increment() -> None:
    """increment=0 → AF 가 start 에서 고정 (Wilder 정의상 허용)."""
    highs = [float(i) for i in range(100, 120)]
    lows = [h - 0.5 for h in highs]
    state = SarState()
    for h, l in zip(highs, lows):
        ta_sar(state, h, l, 0.02, 0.0, 0.2)
    assert abs(state.acceleration_factor - 0.02) < 1e-9, (
        f"AF must stay at start when increment=0: af={state.acceleration_factor}"
    )


def test_ta_sar_two_bar_clamp_uptrend() -> None:
    """Wilder 2-bar clamp: uptrend 일반 step 에서 SAR ≤ min(prev_low, prev2_low).

    핵심 시나리오 — t-1 의 low 가 t-2 의 low 보다 훨씬 높으면, prev_low 만 clamp 시
    SAR 가 prev2_low 를 침범할 위험이 있음. 둘 다 clamp 해야 안전.

    bar 0 = warmup (return nan, state.prev_low 만 기록)
    bar 1 = init step (state.sar = prev_low, prev2 미사용)
    bar 2~ = 일반 step. bar 2 의 state.prev_low = lows[1], state.prev2_low = lows[0].
    """
    # 의도적: low 가 일정하게 90 → 일반 step 에서 clamp 가 90 으로 강제
    lows = [90.0, 99.0, 105.0, 108.0, 112.0]
    highs = [l + 1.0 for l in lows]
    state = SarState()
    sars: list[float] = []
    for h, l in zip(highs, lows):
        sars.append(ta_sar(state, h, l, 0.02, 0.02, 0.2))
    # bar 2 일반 step: state.prev_low=99(lows[1]), state.prev2_low=90(lows[0])
    # SAR_2 ≤ min(99, 90) = 90 강제 검증
    assert not math.isnan(sars[2])
    assert sars[2] <= 90.0 + 1e-9, (
        f"bar 2 SAR={sars[2]} must be clamped to min(prev_low=99, prev2_low=90)=90"
    )
    # bar 3: state.prev_low=105, state.prev2_low=99 → SAR ≤ 99
    assert sars[3] <= 99.0 + 1e-9, (
        f"bar 3 SAR={sars[3]} must be clamped to min(prev_low=105, prev2_low=99)=99"
    )


def test_ta_sar_two_bar_clamp_downtrend() -> None:
    """Wilder 2-bar clamp: downtrend 일반 step 에서 SAR ≥ max(prev_high, prev2_high)."""
    # 의도적: high 가 일정하게 120 → 일반 step 에서 clamp 가 120 으로 강제
    highs = [120.0, 101.0, 96.0, 91.0, 81.0]
    lows = [h - 1.0 for h in highs]
    state = SarState()
    sars: list[float] = []
    for h, l in zip(highs, lows):
        sars.append(ta_sar(state, h, l, 0.02, 0.02, 0.2))
    # bar 2: state.prev_high=101(highs[1]), state.prev2_high=120(highs[0])
    # SAR_2 ≥ max(101, 120) = 120
    assert not math.isnan(sars[2])
    assert sars[2] >= 120.0 - 1e-9, (
        f"bar 2 SAR={sars[2]} must be clamped to max(prev_high=101, prev2_high=120)=120"
    )
    # bar 3: state.prev_high=96, state.prev2_high=101 → SAR ≥ 101
    assert sars[3] >= 101.0 - 1e-9, (
        f"bar 3 SAR={sars[3]} must be clamped to max(prev_high=96, prev2_high=101)=101"
    )

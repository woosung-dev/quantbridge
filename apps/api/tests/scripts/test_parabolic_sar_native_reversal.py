"""실제 TradingView PSAR 캡처의 역전 봉을 작은 상태 fixture로 보존한다."""

import pytest

from src.strategy.pine_v2.stdlib import SarState, ta_sar


@pytest.mark.parametrize(
    ("state", "high", "low", "native_sar"),
    [
        (
            # MddD4giy 1h, 2026-08-17 22:00Z: 이전 상태와 현재 봉은 실제 OHLCV 관측값.
            SarState(
                is_initialized=True,
                is_uptrend=True,
                sar=64200.064,
                extreme_point=64664.0,
                acceleration_factor=0.2,
                prev_high=64407.4,
                prev_low=64261.1,
                prev2_high=64410.2,
                prev2_low=64231.0,
            ),
            64392.6,
            64240.6,
            64664.0,
        ),
        (
            # MddD4giy 1d, 2024-04-23 00:00Z: 반대 방향의 같은 역전 오류.
            SarState(
                is_initialized=True,
                is_uptrend=False,
                sar=67250.47161947387,
                extreme_point=59521.7,
                acceleration_factor=0.08,
                prev_high=67198.9,
                prev_low=64463.1,
                prev2_high=65694.2,
                prev2_low=64200.0,
            ),
            67145.7,
            65750.0,
            59521.7,
        ),
    ],
)
def test_native_reversal_precedes_previous_two_bar_clamp(
    state: SarState, high: float, low: float, native_sar: float
) -> None:
    assert ta_sar(state, high, low) == pytest.approx(native_sar)

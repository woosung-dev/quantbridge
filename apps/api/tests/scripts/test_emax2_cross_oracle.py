"""EMAx2 v4 원문의 NA 비교·not·네 신호 호출을 손계산으로 검증한다."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.pine_validation import oracles


def candles(prices):
    return pd.DataFrame(
        {
            "open": prices,
            "high": np.asarray(prices) + 1,
            "low": np.asarray(prices) - 1,
            "close": prices,
            "volume": 1,
        },
        index=pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC"),
    )


def test_emax2_original_na_equality_and_not_emit_both_directions_before_slow_seed():
    frame = candles([10.0] * 40)
    reviewed = oracles.compute_oracle("emax2_cross", frame, {"marker_offset": 2})
    assert [(event.bar_time, event.direction) for event in reviewed] == [
        (at, direction) for at in frame.index[:29] for direction in ("long", "short")
    ]
    assert all(event.confirmed_at == event.bar_time + pd.Timedelta(hours=1) for event in reviewed)
    assert all(event.display_time == event.bar_time + pd.Timedelta(hours=2) for event in reviewed)
    # 일반 EMA cross에는 원문 eq/not가 없으므로 같은 선두 신호를 넣지 않는다.
    assert oracles.compute_oracle("ema_cross", frame, {"fast": 9, "slow": 30}) == []


@pytest.mark.parametrize("filter_enabled", [True, False])
def test_emax2_original_filter_routes_cross_between_weak_and_strong_calls(filter_enabled):
    frame = candles([10.0, 10.0, 6.0, 6.0, 14.0])
    weak_up, weak_down, strong_up, strong_down = oracles.emax2_cross_conditions(
        frame, {"fast": 1, "slow": 2, "filter": filter_enabled}
    )
    # idx0: cross=NA, strong=False, eq=NA, not eq=True. idx1: seed 뒤 cross=False.
    np.testing.assert_array_equal(weak_up, [True, False, False, False, filter_enabled])
    np.testing.assert_array_equal(weak_down, [True, False, filter_enabled, False, False])
    np.testing.assert_array_equal(strong_up, [False, False, False, False, not filter_enabled])
    np.testing.assert_array_equal(strong_down, [False, False, not filter_enabled, False, False])


def test_emax2_rejects_non_boolean_filter_input():
    with pytest.raises(ValueError, match="filter"):
        oracles.compute_oracle("emax2_cross", candles([10.0] * 40), {"filter": 1})


def test_emax2_width_array_filter_classifies_ready_crosses_without_changing_event_union():
    frame = candles([10.0] * 20 + [20.0, 5.0])
    wide = oracles.emax2_cross_conditions(frame, {"fast": 1, "slow": 2, "filter_length": 10})
    same = oracles.emax2_cross_conditions(frame, {"fast": 1, "slow": 2, "filter_length": 1})
    # 폭이 처음 커진 두 봉은 최근 10개 평균보다 크다. 길이1이면 width==width_aver다.
    assert [np.flatnonzero(flag).tolist() for flag in wide] == [[0], [0], [20], [21]]
    assert [np.flatnonzero(flag).tolist() for flag in same] == [[0, 20], [0, 21], [], []]

"""실제 TradingView v4의 통제 series에서 관측한 비대칭 동률을 고정한다."""

import hashlib
import json
import math
from pathlib import Path

import pytest

from src.strategy.pine_v2.stdlib import IndicatorState, ta_pivothigh, ta_pivotlow

FIXTURE = json.loads(
    (Path(__file__).parents[2] / "fixtures/pine_native/pivot_ties_v4.json").read_text()
)


@pytest.mark.parametrize("function,side", [(ta_pivothigh, "high"), (ta_pivotlow, "low")])
@pytest.mark.parametrize("strength", [1, 2])
def test_pivots_match_native_controlled_series_including_older_ties(function, side, strength):
    """앞쪽 동률 허용과 뒤쪽 동률 거부를 실제 native의 모든 phase 값과 비교한다."""
    state = IndicatorState()
    values = FIXTURE["controlled_series"]["values_by_phase"]
    column = f"pivot_{side}_{strength}_{strength}"
    for index in range(8 * 4):
        phase = index % 8
        actual = function(state, 1, strength, strength, float(values[phase]))
        if index < 8:
            continue
        expected = FIXTURE["observed_plot_values_by_phase"][str(phase)][column]
        if expected is None:
            assert math.isnan(actual), (phase, actual)
        else:
            assert actual == expected, (phase, expected, actual)


def test_native_fixture_has_original_source_hash_and_observed_evidence():
    assert hashlib.sha256(FIXTURE["source_code"].encode()).hexdigest() == FIXTURE["source_sha256"]
    observed = FIXTURE["native_observation"]
    assert observed["compile_success"] is True and observed["source_copyback_verified"] is True
    assert observed["common_closed_rows"] == 299
    assert len(observed["cases"]) == 8
    assert all(case["matching_count"] == case["observed_count"] >= 36 for case in observed["cases"])


@pytest.mark.parametrize("function", [ta_pivothigh, ta_pivotlow])
@pytest.mark.parametrize("strength", [1, 2])
def test_flat_window_remains_unconfirmed(function, strength):
    state = IndicatorState()
    assert all(math.isnan(function(state, 1, strength, strength, 2.0)) for _ in range(20))


@pytest.mark.parametrize("function", [ta_pivothigh, ta_pivotlow])
@pytest.mark.parametrize("strength", [1, 2])
def test_missing_candidate_and_insufficient_history_remain_nan(function, strength):
    state = IndicatorState()
    assert all(
        math.isnan(function(state, 1, strength, strength, float("nan")))
        for _ in range(2 * strength + 1)
    )
    # 결측이 없는 창이 완성된 뒤에는 기존처럼 정상 극값을 감지한다.
    values = [0.0] * strength + [2.0] + [0.0] * strength
    if function is ta_pivotlow:
        values = [-value for value in values]
    actual = [function(state, 1, strength, strength, value) for value in values]
    assert actual[-1] == (2.0 if function is ta_pivothigh else -2.0)

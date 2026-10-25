"""실제 TradingView v4/v5/v6 통제 series에서 관측한 비대칭 동률을 고정한다."""

import hashlib
import json
import math
from pathlib import Path

import pytest

from src.strategy.pine_v2.stdlib import IndicatorState, ta_pivothigh, ta_pivotlow

FIXTURES = [
    json.loads(
        (Path(__file__).parents[2] / f"fixtures/pine_native/pivot_ties_v{version}.json").read_text()
    )
    for version in (4, 5, 6)
]


@pytest.mark.parametrize("function,side", [(ta_pivothigh, "high"), (ta_pivotlow, "low")])
@pytest.mark.parametrize("strength", [1, 2])
@pytest.mark.parametrize("fixture", FIXTURES, ids=("v4", "v5", "v6"))
def test_pivots_match_native_controlled_series_including_older_ties(
    function, side, strength, fixture
):
    """앞쪽 동률 허용과 뒤쪽 동률 거부를 실제 native의 모든 phase 값과 비교한다."""
    state = IndicatorState()
    values = fixture["controlled_series"]["values_by_phase"]
    column = f"pivot_{side}_{strength}_{strength}"
    for index in range(8 * 4):
        phase = index % 8
        actual = function(state, 1, strength, strength, float(values[phase]))
        if index < 8:
            continue
        expected = fixture["observed_plot_values_by_phase"][str(phase)][column]
        if expected is None:
            assert math.isnan(actual), (phase, actual)
        else:
            assert actual == expected, (phase, expected, actual)


@pytest.mark.parametrize("fixture", FIXTURES, ids=("v4", "v5", "v6"))
def test_native_fixture_has_original_source_hash_and_observed_evidence(fixture):
    assert hashlib.sha256(fixture["source_code"].encode()).hexdigest() == fixture["source_sha256"]
    assert fixture["source_code"].startswith(f"//@version={fixture['pine_version']}\n")
    observed = fixture["native_observation"]
    assert observed["compile_success"] is True and observed["source_copyback_verified"] is True
    assert observed["common_closed_rows"] == 299
    assert len(observed["cases"]) == 8
    assert all(case["matching_count"] == case["observed_count"] >= 36 for case in observed["cases"])
    if fixture["pine_version"] in (5, 6):
        assert observed["create_study_count"] == observed["study_completed_count"] == 1
        assert observed["namespace"]["chart_session"].startswith("cs_")
        assert observed["namespace"]["main_series_id"].startswith("sds_")
        assert [plot["title"] for plot in observed["plot_metadata"]] == [
            "controlled_value",
            "phase",
            "pivot_high_1_1",
            "pivot_low_1_1",
            "pivot_high_2_2",
            "pivot_low_2_2",
        ]


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

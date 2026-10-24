"""확장 후보의 실제 계산 의존 함수와 호출 지점별 상태 회귀."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from src.strategy.pine_v2.stdlib import (
    IndicatorState,
    StdlibDispatcher,
    ta_cci,
    ta_cum,
    ta_linreg,
    ta_roc,
    ta_stoch,
    ta_vwma,
)


def test_cumulative_sum_preserves_signed_values_and_call_site_state() -> None:
    state = IndicatorState()
    assert [ta_cum(state, 1, value) for value in (3.0, -2.0, 4.0)] == [3.0, 1.0, 5.0]
    assert ta_cum(state, 2, 7.0) == 7.0
    assert ta_cum(state, 1, 0.0) == 5.0


def test_stochastic_uses_independent_peak_and_valley_series() -> None:
    state = IndicatorState()
    rows = [(11.0, 15.0, 5.0), (12.0, 17.0, 8.0), (13.0, 16.0, 10.0)]
    values = [ta_stoch(state, 1, *row, 3) for row in rows]
    assert values[:2] == pytest.approx([60.0, 100 * (12 - 5) / (17 - 5)])
    assert values[2] == pytest.approx(100 * (13 - 5) / (17 - 5))
    assert ta_stoch(state, 1, 14.0, 16.0, 12.0, 3) == pytest.approx(100 * (14 - 8) / (17 - 8))


def test_stochastic_series_period_can_increase_without_losing_history() -> None:
    state = IndicatorState()
    for value in (1.0, 2.0, 3.0):
        ta_stoch(state, 1, value, value + 1, value - 1, 2)
    assert ta_stoch(state, 1, 4.0, 5.0, 3.0, 4) == 80.0


@pytest.mark.parametrize("period", [0, -1, math.nan, math.inf])
def test_stochastic_invalid_period_does_not_raise(period: float) -> None:
    assert math.isnan(ta_stoch(IndicatorState(), 1, 1.0, 2.0, 0.0, period))


def test_dispatcher_scopes_new_functions_per_user_call_site() -> None:
    dispatcher = StdlibDispatcher()
    dispatcher.push_call_prefix("first")
    assert dispatcher.call("ta.cum", 1, [2.0]) == 2.0
    dispatcher.pop_call_prefix()
    dispatcher.push_call_prefix("second")
    assert dispatcher.call("ta.cum", 1, [7.0]) == 7.0
    dispatcher.pop_call_prefix()
    dispatcher.push_call_prefix("first")
    assert dispatcher.call("ta.cum", 1, [-1.0]) == 1.0
    assert dispatcher.call("ta.stoch", 2, [1.0, 2.0, 0.0, 1]) == 50.0


@pytest.mark.parametrize("offset, expected", [(0, 7.0), (1, 5.0), (-1, 9.0), (4, -1.0)])
def test_linear_regression_evaluates_least_squares_line_at_offset(offset: int, expected: float) -> None:
    state = IndicatorState()
    for value in [1.0, 3.0, 5.0]:
        assert math.isnan(ta_linreg(state, 1, value, 4, offset))
    assert ta_linreg(state, 1, 7.0, 4, offset) == expected


def test_linear_regression_uses_fit_rather_than_last_value_and_recovers_after_na() -> None:
    state = IndicatorState()
    for value in [2.0, 4.0]:
        ta_linreg(state, 1, value, 3, 0)
    # 마지막 값과 다른 최소제곱 근사. x 평균 1, y 평균 3, 기울기 0.5.
    assert ta_linreg(state, 1, 3.0, 3, 0) == 3.5
    assert math.isnan(ta_linreg(state, 1, math.nan, 3, 0))
    assert math.isnan(ta_linreg(state, 1, 6.0, 3, 0))
    assert math.isnan(ta_linreg(state, 1, 8.0, 3, 0))
    assert ta_linreg(state, 1, 10.0, 3, 0) == 10.0



def test_volume_weighted_average_uses_market_volume_and_rolls_window() -> None:
    state = IndicatorState()
    assert math.isnan(ta_vwma(state, 1, 10.0, 2, volume=1.0))
    assert ta_vwma(state, 1, 20.0, 2, volume=3.0) == 17.5
    assert ta_vwma(state, 1, 40.0, 2, volume=1.0) == 25.0
    assert math.isnan(ta_vwma(state, 2, 7.0, 1, volume=0.0))


def test_volume_weighted_average_dispatcher_requires_real_volume() -> None:
    dispatcher = StdlibDispatcher()
    assert math.isnan(dispatcher.call("ta.vwma", 1, [10.0, 1]))
    assert dispatcher.call("ta.vwma", 1, [10.0, 1], volume=5.0) == 10.0



def test_rate_of_change_uses_bar_offset_and_keeps_negative_base_sign() -> None:
    state = IndicatorState()
    assert math.isnan(ta_roc(state, 1, -10.0, 2))
    assert math.isnan(ta_roc(state, 1, -8.0, 2))
    assert ta_roc(state, 1, -5.0, 2) == -50.0
    assert ta_roc(state, 1, -4.0, 2) == -50.0


def test_rate_of_change_zero_base_and_na_do_not_poison_later_offsets() -> None:
    state = IndicatorState()
    assert math.isnan(ta_roc(state, 1, 0.0, 1))
    assert math.isnan(ta_roc(state, 1, 2.0, 1))
    assert math.isnan(ta_roc(state, 1, math.nan, 1))
    assert math.isnan(ta_roc(state, 1, 3.0, 1))
    assert ta_roc(state, 1, 6.0, 1) == 100.0


def test_commodity_channel_index_uses_mean_absolute_deviation_not_standard_deviation() -> None:
    state = IndicatorState()
    assert math.isnan(ta_cci(state, 1, 1.0, 3))
    assert math.isnan(ta_cci(state, 1, 2.0, 3))
    assert ta_cci(state, 1, 3.0, 3) == pytest.approx(100.0)
    # [2, 3, 8]: 평균13/3, 평균절대편차22/9.
    assert ta_cci(state, 1, 8.0, 3) == pytest.approx(100.0)
    assert ta_cci(state, 1, 4.0, 3) == pytest.approx(-100 / 3)
    assert ta_cci(state, 2, 5.0, 1) == 0.0



def test_native_synthetic_rows_preserve_missing_values_flat_carry_and_regression() -> None:
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures/pine_native/expansion_primitives_v5.json"
    fixture = json.loads(fixture_path.read_text())
    assert fixture["schema_version"] == 1
    assert fixture["initial_bar_observed"] is False
    assert hashlib.sha256(fixture["source_code"].encode()).hexdigest() == fixture["source_sha256"]
    rows = fixture["rows"]
    assert len(rows) == fixture["row_count"] == 399
    state = IndicatorState()
    cumulative_base = rows[0]["cum"] - rows[0]["controlled_value"]
    for index, row in enumerate(rows):
        if index:
            assert row["epoch"] - rows[index - 1]["epoch"] == 3600
            assert row["phase"] == (rows[index - 1]["phase"] + 1) % 12
        source = math.nan if row["controlled_value"] is None else row["controlled_value"]
        actual_cum = ta_cum(state, 1, source)
        if row["cum"] is None:
            assert math.isnan(actual_cum)
        else:
            assert actual_cum == row["cum"] - cumulative_base
        actual_stoch = ta_stoch(state, 2, source, source, source, 3)
        actual_linreg = ta_linreg(state, 3, source, 3, 0)
        actual_offset = ta_linreg(state, 4, source, 3, 1)
        # 캡처가 계산 시작 봉을 포함하지 않아 초기 두 봉의 준비 상태는 단정하지 않는다.
        if index < 2:
            continue
        for actual, field in [
            (actual_stoch, "stoch"),
            (actual_linreg, "linreg"),
            (actual_offset, "linreg_offset_1"),
        ]:
            if row[field] is None:
                assert math.isnan(actual), (index, field)
            else:
                assert actual == pytest.approx(row[field], abs=1e-12), (index, field)


@pytest.mark.parametrize("length", [0, -1])
def test_rate_of_change_rejects_nonpositive_period_like_native_runtime(length: int) -> None:
    with pytest.raises(ValueError, match=r"ta\.roc: length must be greater than zero"):
        ta_roc(IndicatorState(), 1, 3.0, length)


def test_native_edges_cover_cci_flat_carry_roc_vwma_and_first_non_na_stochastic() -> None:
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures/pine_native/expansion_edges_v5.json"
    fixture = json.loads(fixture_path.read_text())
    assert hashlib.sha256(fixture["source_code"].encode()).hexdigest() == fixture["source_sha256"]
    assert fixture["controlled_non_na_start_observed"] is True
    assert fixture["invalid_roc_length"]["observed_error"]["ctx"] == {
        "op": ">", "code": "RE10001", "argName": "length", "bar_index": 0,
        "value": 0.0, "funName": "roc",
    }
    state = IndicatorState()
    rows = fixture["rows"]
    assert len(rows) == fixture["row_count"] == 399
    for index, row in enumerate(rows):
        if index:
            assert row["epoch"] - rows[index - 1]["epoch"] == 3600
            assert row["phase"] == (rows[index - 1]["phase"] + 1) % 12
        source = math.nan if row["controlled_value"] is None else row["controlled_value"]
        active = row["window_age"] >= 0
        actual = {
            "cci": ta_cci(state, 1, source, 3),
            "cci_flat": ta_cci(state, 2, 6.0, 3),
            "roc_1": ta_roc(state, 3, source, 1),
            "vwma": ta_vwma(state, 4, source, 3, volume=row["volume"]),
            "stoch_initial": ta_stoch(
                state, 5, 5.0 if active else math.nan, 10.0 if active else math.nan,
                0.0 if active else math.nan, 3,
            ),
            "stoch_inconsistent_flat": ta_stoch(state, 6, 2.0, 1.0, 1.0, 3),
        }
        for field, value in actual.items():
            if index < 2 and field in {"cci", "cci_flat", "roc_1", "vwma"}:
                continue
            if row[field] is None:
                assert math.isnan(value), (index, field)
            else:
                assert value == pytest.approx(row[field], rel=1e-10, abs=1e-10), (index, field)


@pytest.mark.parametrize("version", [5, 6])
def test_native_seeded_stochastic_does_not_carry_for_nonzero_numerator_over_zero(version: int) -> None:
    path = Path(__file__).resolve().parents[2] / f"fixtures/pine_native/expansion_keywords_v{version}.json"
    fixture = json.loads(path.read_text())
    assert hashlib.sha256(fixture["source_code"].encode()).hexdigest() == fixture["source_sha256"]
    state = IndicatorState()
    assert len(fixture["rows"]) == fixture["row_count"] == 399
    for row in fixture["rows"]:
        source, peak, valley = [math.nan if row[key] is None else row[key] for key in ("source", "high", "low")]
        actual = {
            "stoch": ta_stoch(state, 1, source, peak, valley, 3),
            "cum_keywords": ta_cum(state, 2, source),
            "linreg_keywords": ta_linreg(state, 3, source, 3, 1),
            "roc_keywords": ta_roc(state, 4, source, 1),
            "cci_keywords": ta_cci(state, 5, source, 3),
        }
        assert row["stoch"] == row["stoch_keywords"]
        for key, value in actual.items():
            if row[key] is None:
                assert math.isnan(value), (row["age"], key)
            else:
                assert value == pytest.approx(row[key], abs=1e-12), (row["age"], key)

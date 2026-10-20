"""정적 degraded 호출을 지우지 않고 실제로 실행되지 않은 분기만 구분한다."""

from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2.compat import parse_and_run_v2
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical


def _ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [1.0, 1.0],
            "high": [2.0, 2.0],
            "low": [1.0, 1.0],
            "close": [2.0, 2.0],
            "volume": [1.0, 1.0],
        },
        index=pd.date_range("2026-01-01", periods=2, freq="h", tz="UTC"),
    )


def test_fixed_false_input_proves_legacy_security_branch_was_not_executed() -> None:
    source = """//@version=4
study("t")
h = input(false)
x = h ? security(heikinashi(syminfo.tickerid), "60", close) : close
plotshape(x > open)
"""
    coverage = analyze_coverage(source)
    assert coverage.has_degraded
    assert {"security", "heikinashi"} <= set(coverage.degraded_calls)
    run = run_historical(source, _ohlcv(), capture_signals=True, input_overrides={"h": False})
    assert run.degraded_calls_seen == []
    assert [item.value for item in run.signal_trace] == [True, True]
    active = run_historical(source, _ohlcv(), capture_signals=True, input_overrides={"h": True})
    assert "security" in active.degraded_calls_seen


@pytest.mark.parametrize("name", ["security", "request.security", "request.security_lower_tf"])
def test_executed_security_aliases_inside_udf_are_reported_once(name: str) -> None:
    source = f"""//@version=5
indicator("t")
wrapped() =>
    {name}(syminfo.tickerid, "60", close)
x = wrapped()
plotshape(x > open)
"""
    result = run_historical(source, _ohlcv(), capture_signals=True)
    assert result.degraded_calls_seen == [name]


def test_called_heikinashi_is_reported_but_unexecuted_function_body_is_not() -> None:
    source = """//@version=5
indicator("t")
unused() =>
    request.security(syminfo.tickerid, "60", close)
x = heikinashi(syminfo.tickerid)
plotshape(true)
"""
    result = run_historical(source, _ohlcv(), capture_signals=True)
    assert result.degraded_calls_seen == ["heikinashi"]


def test_user_function_shadowing_security_does_not_report_a_builtin_call() -> None:
    source = """//@version=5
indicator("t")
security(x) =>
    x
x = security(close)
plotshape(x > open)
"""
    assert run_historical(source, _ohlcv(), capture_signals=True).degraded_calls_seen == []


def test_trace_disabled_keeps_degraded_execution_and_results_unchanged() -> None:
    source = """//@version=5
indicator("t")
x = request.security(syminfo.tickerid, "60", close)
"""
    run = run_historical(source, _ohlcv())
    assert run.degraded_calls_seen == []
    assert run.final_state["x"] == 2.0


@pytest.mark.parametrize("active", [True, False])
def test_nop_arguments_are_not_mistaken_for_unexecuted_degraded_calls(active: bool) -> None:
    condition = "true" if active else "false"
    source = f'''//@version=5
indicator("t")
plot({condition} ? request.security(syminfo.tickerid, "60", close) : close)
plotshape(close > open)
'''
    run = run_historical(source, _ohlcv(), capture_signals=True)
    assert run.degraded_calls_seen == (["request.security"] if active else [])


def test_marker_non_condition_arguments_also_report_degraded_execution() -> None:
    source = '''//@version=5
indicator("t")
plotshape(true, color=request.security(syminfo.tickerid, "60", color.green))
'''
    run = run_historical(source, _ohlcv(), capture_signals=True)
    assert run.degraded_calls_seen == ["request.security"]


def test_explicit_timeframe_is_exact_and_missing_context_is_reported() -> None:
    source = '//@version=5\nindicator("t")\nx = timeframe.period\n'
    assert run_historical(source, _ohlcv(), capture_signals=True).degraded_calls_seen == [
        "timeframe.period"
    ]
    explicit = run_historical(source, _ohlcv(), capture_signals=True, timeframe="1h")
    assert explicit.degraded_calls_seen == []
    assert explicit.final_state["x"] == "60"


def test_virtual_runner_returns_actual_degraded_observations() -> None:
    source = """//@version=5
indicator("t")
x = request.security(syminfo.tickerid, "60", close)
alertcondition(x > open, "", "BUY")
"""
    result = parse_and_run_v2(source, _ohlcv(), capture_signals=True)
    assert result.virtual is not None
    assert result.virtual.degraded_calls_seen == ["request.security"]


@pytest.mark.parametrize("condition", ["true", "false"])
def test_legacy_iff_reports_degraded_call_in_both_eager_arguments(condition: str) -> None:
    remote = 'security(syminfo.tickerid, "60", close)'
    first, second = (remote, "close") if condition == "false" else ("close", remote)
    source = f'''//@version=4
study("t")
x = iff({condition}, {first}, {second})
'''
    result = run_historical(source, _ohlcv(), capture_signals=True)
    assert result.degraded_calls_seen == ["security"]


@pytest.mark.parametrize("capture", [True, False])
@pytest.mark.parametrize("condition,expected", [("true", 10), ("false", 20)])
def test_legacy_iff_evaluates_each_argument_once_even_with_capture_disabled(
    capture: bool, condition: str, expected: int
) -> None:
    source = f'''//@version=4
study("t")
var counts = array.new_int(1, 0)
bump(value) =>
    array.set(counts, 0, array.get(counts, 0) + 1)
    value
x = iff({condition}, bump(10), bump(20))
calls = array.get(counts, 0)
'''
    result = run_historical(source, _ohlcv(), capture_signals=capture)
    assert result.var_series["calls"] == [2, 4]
    assert result.var_series["x"] == [expected, expected]


@pytest.mark.parametrize("name", ["tostring", "str.tostring"])
def test_string_format_argument_reports_actual_degraded_call(name: str) -> None:
    source = f'''//@version=5
indicator("t")
caption = {name}(close, request.security(syminfo.tickerid, "60", "#.##"))
'''
    result = run_historical(source, _ohlcv(), capture_signals=True)
    assert result.degraded_calls_seen == ["request.security"]
    assert result.final_state["caption"] == "2.0"


@pytest.mark.parametrize("capture,expected", [(True, [2, 4]), (False, [1, 2])])
def test_string_value_and_format_are_evaluated_once_with_legacy_capture_off_behavior(
    capture: bool, expected: list[int]
) -> None:
    source = '''//@version=5
indicator("t")
var counts = array.new_int(1, 0)
bump(value) =>
    array.set(counts, 0, array.get(counts, 0) + 1)
    value
caption = str.tostring(bump(close), bump("#.##"))
calls = array.get(counts, 0)
'''
    result = run_historical(source, _ohlcv(), capture_signals=capture)
    assert result.var_series["calls"] == expected
    assert result.final_state["caption"] == "2.0"

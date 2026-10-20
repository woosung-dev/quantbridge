"""실제 호출 위치의 신호 관찰과 시간 context를 검증한다. DB/외부 API는 쓰지 않는다."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from src.strategy.pine_v2.compat import parse_and_run_v2
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def _ohlcv(closes: list[float], *, dated: bool = True) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "open": [10.0] * len(closes),
            "high": [max(close, 10.0) for close in closes],
            "low": [min(close, 10.0) for close in closes],
            "close": closes,
            "volume": [1.0] * len(closes),
        }
    )
    if dated:
        frame.index = pd.date_range("2026-01-01", periods=len(frame), freq="h", tz="UTC")
    return frame


def test_trace_is_opt_in() -> None:
    source = '//@version=5\nindicator("t")\nplotshape(true)\n'
    assert run_historical(source, _ohlcv([10.0])).signal_trace == []


@pytest.mark.parametrize("capture", [False, True])
def test_rendering_arguments_are_evaluated_without_requiring_trace(capture: bool) -> None:
    source = '//@version=5\nindicator("t")\nplotshape(undefined_name)\n'
    with pytest.raises(PineRuntimeError, match="Undefined name: undefined_name"):
        run_historical(source, _ohlcv([10.0]), capture_signals=capture)


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize(
    "rendering_call",
    ["plot(bump(close))", "plotshape(bump(close) > 0)", "caption = str.tostring(bump(close))"],
)
def test_trace_preserves_rendering_argument_side_effects_and_strategy_orders(
    capture: bool, rendering_call: str
) -> None:
    # 배열을 변경하는 호출도 원본의 실행 의미다. 관측 여부로 주문이 달라지면 안 된다.
    source = f"""//@version=5
strategy("t")
var counts = array.new_int(1, 0)
bump(value) =>
    array.set(counts, 0, array.get(counts, 0) + 1)
    value
{rendering_call}
if array.get(counts, 0) == 1
    strategy.entry("L", strategy.long, qty=1)
observed = array.get(counts, 0)
"""
    result = run_historical(source, _ohlcv([10.0, 11.0]), capture_signals=capture)
    assert result.var_series["observed"] == [1, 2]
    assert result.strategy_state.position_size == 1
    assert result.strategy_state.open_trades["L"].entry_bar == 0
    assert len(result.signal_trace) == (
        2 if capture and rendering_call.startswith("plotshape") else 0
    )


def test_trace_uses_actual_scope_call_order_and_values_before_reassignment() -> None:
    source = """//@version=5
indicator("t")
signal = close > open
if signal
    plotshape(signal, offset=-2)
signal := false
plotchar(signal, offset=1)
if close < open
    alert("BUY")
"""
    trace = run_historical(source, _ohlcv([11.0, 9.0]), capture_signals=True).signal_trace
    assert [(item.function, item.source_line, item.value) for item in trace] == [
        ("plotshape", 5, True),
        ("plotchar", 7, False),
        ("plotchar", 7, False),
        ("alert", 9, True),
    ]
    assert [item.source_column for item in trace] == [4, 0, 0, 4]
    assert [item.bar_index for item in trace] == [0, 0, 1, 1]
    assert [item.marker_offset for item in trace] == [-2, 1, 1, 0]
    assert trace[0].bar_open_time == datetime(2026, 1, 1, tzinfo=UTC)
    assert trace[-1].bar_open_time == datetime(2026, 1, 1, 1, tzinfo=UTC)


def test_inline_stateful_first_argument_is_evaluated_once() -> None:
    source = '//@version=5\nindicator("t")\nplotarrow(ta.change(close))\n'
    trace = run_historical(source, _ohlcv([10.0, 11.0, 13.0]), capture_signals=True).signal_trace
    assert [item.value for item in trace] == [None, 1.0, 2.0]


def test_named_and_positional_conditions_offsets_preserve_false_and_numeric_values() -> None:
    source = """//@version=5
indicator("t")
plotshape(series=close > 10, offset=-1)
plotchar(false, "", "", location.abovebar, color.red, 2)
plotarrow(-3, "", color.red, color.green, -4)
alertcondition(condition=close < 10, title="t", message="SELL")
"""
    trace = run_historical(source, _ohlcv([10.0]), capture_signals=True).signal_trace
    assert [item.value for item in trace] == [False, False, -3, False]
    assert [item.marker_offset for item in trace] == [-1, 2, -4, 0]


def test_trace_is_not_truncated_by_variable_history_ring() -> None:
    source = '//@version=5\nindicator("t")\nplotshape(close > open)\n'
    trace = run_historical(
        source, _ohlcv([11.0] * 600), capture_signals=True, capture_history=False
    ).signal_trace
    assert len(trace) == 600
    assert [item.bar_index for item in trace] == list(range(600))


def test_trace_without_timestamps_preserves_unknown_time() -> None:
    source = '//@version=5\nindicator("t")\nplotshape(true)\n'
    trace = run_historical(source, _ohlcv([10.0], dated=False), capture_signals=True).signal_trace
    assert trace[0].bar_open_time is None


@pytest.mark.parametrize("track", ["S", "A", "M"])
def test_dispatcher_forwards_trace_and_timeframe_to_each_track(track: str) -> None:
    declaration = 'strategy("t")' if track == "S" else 'indicator("t")'
    signal = 'alertcondition(true, "", "BUY")' if track == "A" else "plotshape(true)"
    source = f"//@version=5\n{declaration}\ntf = timeframe.period\n{signal}\n"
    result = parse_and_run_v2(source, _ohlcv([10.0]), capture_signals=True, timeframe="4h")
    assert result.track == track
    run = result.virtual if track == "A" else result.historical
    assert run is not None
    assert len(run.signal_trace) == 1
    assert run.signal_trace[0].value is True


def test_virtual_trace_does_not_reevaluate_stateful_alert_condition() -> None:
    source = """//@version=5
indicator("t")
alertcondition(ta.change(close) > 0, "", "BUY")
"""
    result = parse_and_run_v2(source, _ohlcv([10.0, 11.0, 13.0]), capture_signals=True)
    assert result.virtual is not None
    assert [item.value for item in result.virtual.signal_trace] == [False, True, True]


@pytest.mark.parametrize(
    ("timeframe", "period", "multiplier", "is_minutes", "is_daily"),
    [("1h", "60", 60, True, False), ("4h", "240", 240, True, False), ("1d", "D", 1, False, True)],
)
def test_explicit_timeframe_and_actual_utc_time(
    timeframe: str, period: str, multiplier: int, is_minutes: bool, is_daily: bool
) -> None:
    source = """//@version=5
indicator("t")
t = time
p = timeframe.period
m = timeframe.multiplier
minutes = timeframe.isminutes
daily = timeframe.isdaily
seconds = timeframe.isseconds
weekly = timeframe.isweekly
monthly = timeframe.ismonthly
"""
    frame = _ohlcv([10.0])
    frame.index = pd.DatetimeIndex(["2026-01-01 09:00:00+09:00"])
    state = run_historical(source, frame, timeframe=timeframe).final_state
    assert state["t"] == int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000)
    assert state["p"] == period
    assert state["m"] == multiplier
    assert state["minutes"] is is_minutes
    assert state["daily"] is is_daily
    assert state["seconds"] is False
    assert state["weekly"] is False
    assert state["monthly"] is False


def test_missing_context_preserves_legacy_time_and_timeframe_defaults() -> None:
    source = """//@version=5
indicator("t")
t = time
p = timeframe.period
m = timeframe.multiplier
"""
    state = run_historical(source, _ohlcv([10.0], dated=False)).final_state
    assert state == {"t": 50 * 365 * 86_400 * 1000, "p": "1D", "m": 0}


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize(
    ("timeframe", "legacy", "current"),
    [
        ("1d", "D", "1D"),
        ("1w", "W", "1W"),
        ("1M", "M", "1M"),
        ("2d", "2D", "2D"),
        ("2w", "2W", "2W"),
        ("2M", "2M", "2M"),
        ("1h", "60", "60"),
        ("1m", "1", "1"),
        ("1s", "1S", "1S"),
    ],
)
def test_timeframe_period_uses_actual_source_version(
    version: int, timeframe: str, legacy: str, current: str
) -> None:
    declaration = 'study("t")' if version == 4 else 'indicator("t")'
    source = f"//@version={version}\n{declaration}\np = timeframe.period\n"
    result = run_historical(source, _ohlcv([10.0]), timeframe=timeframe)
    assert result.final_state["p"] == (legacy if version < 6 else current)


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize("track", ["S", "A", "M"])
def test_dispatcher_preserves_source_version_for_timeframe_context(
    version: int, track: str
) -> None:
    declaration = (
        'strategy("t")'
        if track == "S"
        else 'study("t")'
        if version == 4
        else 'indicator("t")'
    )
    expected = "D" if version < 6 else "1D"
    marker = f'timeframe.period == "{expected}"'
    signal = f'alertcondition({marker}, "", "BUY")' if track == "A" else f"plotshape({marker})"
    source = f"//@version={version}\n{declaration}\n{signal}\n"
    result = parse_and_run_v2(source, _ohlcv([10.0]), timeframe="1d", capture_signals=True)
    run = result.virtual if track == "A" else result.historical
    assert run is not None
    assert [row.value for row in run.signal_trace] == [True]


def test_source_string_does_not_override_actual_version_annotation() -> None:
    source = '''//@version=6
indicator("t")
caption = "//@version=4"
p = timeframe.period
'''
    result = run_historical(source, _ohlcv([10.0]), timeframe="1d")
    assert result.final_state["p"] == "1D"


@pytest.mark.parametrize("version", [4, 5, 6])
def test_versioned_source_without_explicit_timeframe_keeps_legacy_fallback(version: int) -> None:
    source = f"//@version={version}\np = timeframe.period\n"
    assert run_historical(source, _ohlcv([10.0])).final_state["p"] == "1D"

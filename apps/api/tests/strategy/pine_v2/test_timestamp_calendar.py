"""합성 달력이 실제 봉 시각의 날짜 필터를 앞당기는 회귀를 막는다."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def _run(expression: str) -> int | float:
    frame = pd.DataFrame(
        {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]}
    )
    source = f'//@version=5\nindicator("t")\nx = {expression}\n'
    return run_historical(source, frame).final_state["x"]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("timestamp(1970, 1, 1)", 0),
        ("timestamp(1969, 12, 31, 23, 59, 59)", -1000),
        ("timestamp(2024, 2, 29, 12, 34, 56)", 1709210096000),
        ("timestamp(2026, 1, 10, 0, 0)", 1768003200000),
        ("timestamp(2024, 3, 1) - timestamp(2024, 2, 28)", 172800000),
        ("timestamp(2025, 3, 1) - timestamp(2025, 2, 28)", 86400000),
        ("timestamp(year=2026, month=1, day=10, second=1)", 1768003201000),
        ('timestamp("UTC", 2026, 1, 10)', 1768003200000),
        ('timestamp(timezone="Etc/UTC", year=2026, month=1, day=10)', 1768003200000),
    ],
)
def test_timestamp_uses_actual_utc_calendar(expression: str, expected: int) -> None:
    assert _run(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("timestamp(2026, -2, 1, 0, 0)", datetime(2025, 10, 1, tzinfo=UTC)),
        ("timestamp(2026, 0, 1)", datetime(2025, 12, 1, tzinfo=UTC)),
        ("timestamp(2026, 13, 1)", datetime(2027, 1, 1, tzinfo=UTC)),
        ("timestamp(2026, 1, 0)", datetime(2025, 12, 31, tzinfo=UTC)),
        ("timestamp(2026, 1, 32)", datetime(2026, 2, 1, tzinfo=UTC)),
        ("timestamp(2025, 2, 29)", datetime(2025, 3, 1, tzinfo=UTC)),
        ("timestamp(2024, 2, 30)", datetime(2024, 3, 1, tzinfo=UTC)),
        ("timestamp(2026, 1, 1, -1, 60, 60)", datetime(2026, 1, 1, 0, 1, tzinfo=UTC)),
        ('timestamp("UTC", 2026, -2, 32)', datetime(2025, 11, 1, tzinfo=UTC)),
        ("timestamp(year=2026, month=-2, day=1)", datetime(2025, 10, 1, tzinfo=UTC)),
    ],
)
def test_timestamp_normalizes_calendar_overflow(expression: str, expected: datetime) -> None:
    assert _run(expression) == int(expected.timestamp() * 1000)


def test_date_filter_changes_only_at_requested_start_on_dated_bars() -> None:
    frame = pd.DataFrame(
        {
            "open": [1.0] * 3,
            "high": [1.0] * 3,
            "low": [1.0] * 3,
            "close": [1.0] * 3,
            "volume": [1.0] * 3,
        },
        index=pd.DatetimeIndex(["2026-01-01T00:00Z", "2026-01-09T00:00Z", "2026-01-10T00:00Z"]),
    )
    source = """//@version=5
indicator("t")
plotshape(time >= timestamp(2026, 1, 10, 0, 0))
"""
    trace = run_historical(source, frame, capture_signals=True).signal_trace
    assert [observation.value for observation in trace] == [False, False, True]
    assert trace[-1].bar_open_time == datetime(2026, 1, 10, tzinfo=UTC)


def test_missing_time_cannot_establish_inclusion_in_a_wide_date_filter() -> None:
    """시각이 없으면 기간 포함 여부는 미상이며 필터를 통과시키지 않는다."""
    assert math.isnan(_run("time"))
    assert math.isnan(_run("time >= timestamp(1970, 1, 1, 0, 0)"))
    value = _run("time >= timestamp(1970, 1, 1, 0, 0) and time <= timestamp(2100, 1, 1, 0, 0)")
    assert value is False


@pytest.mark.parametrize("expression", ["timestamp(na, 1, 1)", "timestamp(1e309, 1, 1)"])
def test_non_finite_timestamp_input_is_na(expression: str) -> None:
    assert math.isnan(_run(expression))


@pytest.mark.parametrize(
    "expression",
    [
        'timestamp("10 Jan 2026")',
        'timestamp("America/New_York", 2026, 1, 10)',
        "timestamp(10000, 1, 1)",
        "timestamp(9999, 12, 32)",
        "timestamp(2026, 1, 1000000000000000000)",
        "timestamp(2026, 1)",
    ],
)
def test_unsupported_timestamp_overloads_and_calendar_range_fail_closed(expression: str) -> None:
    with pytest.raises(PineRuntimeError, match="timestamp:"):
        _run(expression)

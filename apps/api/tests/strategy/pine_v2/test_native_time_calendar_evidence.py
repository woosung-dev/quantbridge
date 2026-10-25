"""실제 TV 통제 probe의 비금융 스칼라만 재사용한다. 원본 전략/원시 인증정보는 없다."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, _calendar_part
from src.strategy.pine_v2.runtime import PersistentStore

FIXTURE = Path(__file__).parents[2] / "fixtures/pine_native/timeframe_calendar_v5_v6.json"
EVIDENCE = json.loads(FIXTURE.read_text())


def test_controlled_sources_are_bound_to_observed_source_hashes():
    assert EVIDENCE["raw_auth_or_prices_included"] is False
    for probe in EVIDENCE["probes"]:
        assert hashlib.sha256(probe["source"].encode()).hexdigest() == probe["source_sha256"]
        assert probe["scope"] == "controlled_time_diagnostic_not_strategy_reference"
        assert probe["common_closed_bars"] > 1000


def test_native_v6_calendar_and_time_open_values():
    for case in EVIDENCE["v6_calendar_cases"]:
        stamp = pd.Timestamp(case["time"], unit="ms", tz="UTC")
        frame = pd.DataFrame(
            {k: [100.0, 100.0] for k in ("open", "high", "low", "close", "volume")}
        )
        bar = BarContext(
            frame,
            timestamps=pd.DatetimeIndex([stamp - pd.Timedelta(hours=1), stamp]),
            timeframe="1h",
        )
        bar.bar_index = 1
        interpreter = Interpreter(bar, PersistentStore())
        for unit in ("D", "W", "M"):
            assert interpreter._timeframe_open(unit) == case["time_" + unit]
            assert (
                interpreter._timeframe_open(unit) != interpreter._timeframe_open(unit, 1)
            ) == bool(case["change_" + unit])
        for field in ("year", "month", "dayofweek", "hour", "minute"):
            assert _calendar_part(field, case["time"]) == case[field]


def test_native_v5_all_month_constants_and_both_versions_initial_change():
    frame = pd.DataFrame(
        {k: [100.0] for k in ("open", "high", "low", "close", "volume")},
        index=pd.to_datetime(["2026-01-01T00:00Z"]),
    )
    for probe in EVIDENCE["probes"]:
        version = probe["pine_version"]
        body = 'first_day=timeframe.change("D")\nfirst_week=timeframe.change("W")\nfirst_month=timeframe.change("M")\n'
        months = range(1, 13) if version == 5 else (1, 3)
        body += "".join(f'm{i}=timeframe.in_seconds("{i}M")\n' for i in months)
        result = run_historical(
            f'//@version={version}\nindicator("native constants")\n' + body,
            frame,
            timeframe="1h",
            strict=True,
        )
        for period in ("day", "week", "month"):
            assert result.final_state["first_" + period] == bool(
                probe["constants"]["first_" + period + "_change"][0]
            )
        for i in months:
            key = (
                f"month_{i}_seconds"
                if version == 5
                else "month_seconds"
                if i == 1
                else "three_month_seconds"
            )
            assert result.final_state[f"m{i}"] == probe["constants"][key][0]


def test_native_scalar_parameter_history_inside_own_loop():
    # 통제 fixture만 재생한다. 실제 원본/생성 전략이나 시장 가격은 실행하지 않는다.
    cases = EVIDENCE["v5_parameter_history_cases"]
    values = [float(i + 1) for i in range(max(c["bar_index"] for c in cases) + 1)]
    frame = pd.DataFrame(dict.fromkeys(("open", "high", "low", "close", "volume"), values))
    source = """//@version=5
indicator("native parameter fixture")
f(x) =>
    total=0.0
    for j=0 to 2
        total += nz(x[j],0)
    total
a=f(close)
b=f(close*10)
"""
    result = run_historical(source, frame, strict=True)
    for case in cases:
        index = case["bar_index"]
        assert (
            result.state_history[index]["a"] == case["own_loop_actual"] == case["own_loop_expected"]
        )
        assert (
            result.state_history[index]["b"]
            == case["own_loop_actual_ten"]
            == case["own_loop_expected_ten"]
        )

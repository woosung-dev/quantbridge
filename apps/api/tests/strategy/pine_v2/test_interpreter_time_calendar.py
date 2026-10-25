"""UTC Bybit 달력과 명시 주기 문맥의 Pine 의미를 확인한다."""

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def run(body, *, times=None, timeframe=None, version=6):
    frame = pd.DataFrame(
        {
            field: [100.0] * (len(times) if times is not None else 2)
            for field in ("open", "high", "low", "close", "volume")
        }
    )
    if times is not None:
        frame.index = pd.to_datetime(times, utc=True)
    return run_historical(
        f'//@version={version}\nindicator("calendar")\n{body}\n',
        frame,
        timeframe=timeframe,
        strict=True,
        capture_signals=True,
    )


def test_calendar_fields_follow_actual_bar_open_utc_leap_and_year_boundaries():
    result = run(
        "y=year\nm=month\nd=dayofmonth\nw=dayofweek\nh=hour\nn=minute\ns=second",
        times=[
            "2024-02-29T23:59:59Z",
            "2024-03-01T00:00:00Z",
            "2025-12-31T23:59:00Z",
            "2026-01-01T00:00:00Z",
        ],
    )
    assert result.var_series["y"] == [2024, 2024, 2025, 2026]
    assert result.var_series["m"] == [2, 3, 12, 1]
    assert result.var_series["d"] == [29, 1, 31, 1]
    assert result.var_series["w"] == [5, 6, 4, 5]
    assert result.var_series["h"] == [23, 0, 23, 0]
    assert result.var_series["n"] == [59, 0, 59, 0]
    assert result.var_series["s"] == [59, 0, 0, 0]


def test_calendar_history_uses_prior_bar_date_and_initial_na():
    result = run(
        "prior=year[1]\nday_prior=dayofmonth[1]", times=["2025-12-31T23:00Z", "2026-01-01T00:00Z"]
    )
    assert math.isnan(result.var_series["prior"][0])
    assert result.var_series["prior"][1] == 2025
    assert result.var_series["day_prior"][1] == 31


def test_dayofweek_constants_use_sunday_one_and_monday_two():
    result = run(
        "d=dayofweek\nsun=dayofweek.sunday\nmon=dayofweek.monday\nsat=dayofweek.saturday",
        times=["2026-01-04T00:00Z", "2026-01-05T00:00Z"],
    )
    assert result.var_series["d"] == [1, 2]
    assert [result.final_state[k] for k in ("sun", "mon", "sat")] == [1, 2, 7]


def test_explicit_iana_zone_obeys_both_dst_transitions_and_keyword_order():
    result = run(
        'a=hour(timestamp("UTC",2026,3,8,6,59),"America/New_York")\nb=hour(timezone="America/New_York",time=timestamp("UTC",2026,3,8,7,0))\nc=hour(timestamp("UTC",2026,11,1,5,59),"America/New_York")\nd=hour(timestamp("UTC",2026,11,1,6,0),"America/New_York")\ne=minute(timestamp("UTC",2026,11,1,5,59),"America/New_York")\nf=minute(timestamp("UTC",2026,11,1,6,0),"America/New_York")'
    )
    assert [result.final_state[k] for k in "abcdef"] == [1, 3, 1, 1, 59, 0]


@pytest.mark.parametrize(
    "expression",
    [
        'hour(0,"Unknown/Zone")',
        'hour(0,"UTC+3")',
        "hour(true)",
        "year(1.5)",
        "month()",
        "hour(0,time=1)",
        'minute(timezone="UTC",0)',
        "year(stamp=0)",
    ],
)
def test_invalid_calendar_overloads_fail_closed(expression):
    with pytest.raises(PineRuntimeError):
        run(f"x={expression}")


def test_missing_calendar_context_is_na_and_explicitly_degraded():
    result = run("y=year\np=month[1]\nx=hour(na)")
    assert all(math.isnan(result.final_state[k]) for k in ("y", "p", "x"))
    assert set(result.degraded_calls_seen) == {"year", "month"}


@pytest.mark.parametrize(
    "value,expected",
    [
        ('"1S"', 1),
        ('"45S"', 45),
        ('"60"', 3600),
        ('"240"', 14400),
        ('"1440"', 86400),
        ('"D"', 86400),
        ('"3D"', 259200),
        ('"W"', 604800),
        ('"2W"', 1209600),
    ],
)
def test_explicit_timeframe_conversion_uses_pine_units(value, expected):
    assert run(f"x=timeframe.in_seconds({value})").final_state["x"] == expected


@pytest.mark.parametrize(
    "expression",
    [
        'timeframe.in_seconds("2M")',
        'timeframe.in_seconds("13M")',
        'timeframe.in_seconds("1H")',
        'timeframe.in_seconds("2S")',
        'timeframe.in_seconds("0D")',
        'timeframe.in_seconds("1441")',
        'timeframe.in_seconds("1T")',
        "timeframe.in_seconds(true)",
        'timeframe.in_seconds(tf="60")',
        'timeframe.in_seconds(timeframe="60",timeframe="240")',
    ],
)
def test_unverified_calendar_conversion_and_invalid_timeframes_are_rejected(expression):
    with pytest.raises(PineRuntimeError):
        run(f"x={expression}")


@pytest.mark.parametrize(
    "timeframe,seconds,period,intraday",
    [
        ("1h", 3600, "60", True),
        ("4h", 14400, "240", True),
        ("1d", 86400, "1D", False),
        ("1w", 604800, "1W", False),
    ],
)
def test_current_timeframe_requires_and_uses_explicit_runtime_context(
    timeframe, seconds, period, intraday
):
    result = run(
        'x=timeframe.in_seconds()\ny=timeframe.in_seconds(timeframe="")\np=timeframe.period\ni=timeframe.isintraday',
        timeframe=timeframe,
    )
    assert result.final_state["x"] == result.final_state["y"] == seconds
    assert result.final_state["p"] == period
    assert result.final_state["i"] is intraday
    assert not result.degraded_calls_seen


def test_missing_timeframe_context_is_not_assumed_daily():
    with pytest.raises(PineRuntimeError, match="explicit timeframe context"):
        run("x=timeframe.in_seconds()")
    result = run(
        "x=timeframe.multiplier\ny=timeframe.isdaily\nz=timeframe.isintraday\np=timeframe.period"
    )
    assert set(result.degraded_calls_seen) == {
        "timeframe.multiplier",
        "timeframe.isdaily",
        "timeframe.isintraday",
        "timeframe.period",
    }


def test_math_constants_and_existing_v4_scalar_aliases():
    result = run("p=math.pi\ne=math.e\nx=ceil(-1.2)\ny=sign(-3)\nz=log10(100)", version=4)
    assert result.final_state["p"] == math.pi
    assert result.final_state["e"] == math.e
    assert [result.final_state[k] for k in ("x", "y", "z")] == [-1, -1, 2]


def test_calendar_keywords_validate_before_side_effects_and_keep_source_order():
    with pytest.raises(PineRuntimeError, match="unknown calendar argument"):
        run("a=array.new_int()\nx=hour(unknown=array.get(a,99))")
    result = run(
        'a=array.new_int()\nf(values,order,value) =>\n    array.push(values,order)\n    value\nx=hour(timezone=f(a,1,"UTC"),time=f(a,2,0))\nfirst=array.get(a,0)\nsecond=array.get(a,1)\nsize=array.size(a)'
    )
    assert [result.final_state[k] for k in ("first", "second", "size", "x")] == [1, 2, 2, 0]


def test_time_function_uses_exact_utc_daily_weekly_monthly_calendar_boundaries():
    times = ["2024-02-29T23:00Z", "2024-03-01T00:00Z", "2024-03-03T23:00Z", "2024-03-04T00:00Z"]
    result = run(
        'd=time("D")\nw=time("W")\nm=time("M")\nh=time("240")', times=times, timeframe="1h"
    )

    def epoch(values):
        return [pd.Timestamp(value).value // 1000000 for value in values]

    assert result.var_series["d"] == epoch(
        ["2024-02-29T00:00Z", "2024-03-01T00:00Z", "2024-03-03T00:00Z", "2024-03-04T00:00Z"]
    )
    assert result.var_series["w"] == epoch(["2024-02-26T00:00Z"] * 3 + ["2024-03-04T00:00Z"])
    assert result.var_series["m"] == epoch(["2024-02-01T00:00Z"] + ["2024-03-01T00:00Z"] * 3)
    assert result.var_series["h"] == epoch(
        ["2024-02-29T20:00Z", "2024-03-01T00:00Z", "2024-03-03T20:00Z", "2024-03-04T00:00Z"]
    )


def test_time_function_does_not_replace_week_open_sample_with_week_close():
    result = run(
        'opening=time("W")\nnew_week=ta.change(opening) != 0\nsampled=ta.valuewhen(new_week,bar_index,0)',
        times=["2024-03-03T23:00Z", "2024-03-04T00:00Z", "2024-03-04T01:00Z"],
        timeframe="1h",
    )
    assert result.var_series["new_week"][1:] == [True, False]
    assert result.var_series["sampled"][1:] == [1, 1]


@pytest.mark.parametrize(
    "expression,timeframe",
    [
        ('time("D")', None),
        ('time("30")', "1h"),
        ('time("2D")', "1h"),
        ('time("2W")', "1h"),
        ('time("3M")', "1h"),
        ('time("7")', "1h"),
        ('time("D","24x7")', "1h"),
        ("time()", "1h"),
    ],
)
def test_time_function_unverified_context_anchors_and_sessions_fail_closed(expression, timeframe):
    with pytest.raises(PineRuntimeError):
        run(f"x={expression}", times=["2026-01-01T00:00Z"], timeframe=timeframe)


def test_native_v6_first_change_is_false_and_calendar_boundary_is_true():
    result = run(
        'd=timeframe.change("D")\nw=timeframe.change("W")\nm=timeframe.change("M")',
        times=["2024-02-29T23:00Z", "2024-03-01T00:00Z", "2024-03-03T23:00Z", "2024-03-04T00:00Z"],
        timeframe="1h",
    )
    assert result.var_series["d"] == [False, True, True, True]
    assert result.var_series["w"] == [False, False, False, True]
    assert result.var_series["m"] == [False, True, False, False]


def test_native_v6_month_numeric_values_are_separate_from_calendar_boundaries():
    result = run('a=timeframe.in_seconds("M")\nb=timeframe.in_seconds("3M")')
    assert result.final_state["a"] == 2628003
    assert result.final_state["b"] == 7884009


@pytest.mark.parametrize("version", [5, 6])
def test_native_both_versions_first_change_is_false(version):
    result = run(
        'x=timeframe.change("D")',
        times=["2026-01-01T00:00Z", "2026-01-02T00:00Z"],
        timeframe="1h",
        version=version,
    )
    assert result.var_series["x"] == [False, True]


@pytest.mark.parametrize("count", range(1, 13))
def test_native_v5_all_month_multipliers_have_observed_integer_conversion(count):
    result = run(f'x=timeframe.in_seconds("{count}M")', version=5)
    observed = [
        2628003,
        5256006,
        7884009,
        10512012,
        13140015,
        15768018,
        18396021,
        21024024,
        23652027,
        26280030,
        28908033,
        31536036,
    ]
    assert result.final_state["x"] == observed[count - 1]


def test_dynamic_change_timeframe_is_rejected_instead_of_reusing_wrong_history():
    with pytest.raises(PineRuntimeError, match="dynamic timeframe"):
        run(
            'tf=bar_index==0?"D":"W"\nx=timeframe.change(tf)',
            times=["2026-01-01T00:00Z", "2026-01-01T01:00Z"],
            timeframe="1h",
        )

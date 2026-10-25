"""관측한 v4/v5 초기 alert NA를 false로 바꾸지 않고 비교창에서 제외한다."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from scripts.pine_validation.native_capture import _frames, parse_native_capture
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, T0, _frame, _payload


def missing_capture(version=5, value=1e100, missing_index=0):
    source = SOURCE.replace("//@version=5", f"//@version={version}").replace(
        "buy = close > open", "buy = ta.sma(close, length) > open"
    )
    if version == 4:
        source = (
            source.replace('indicator("demo")', 'study("demo")')
            .replace("input.int(", "input(")
            .replace("ta.sma(", "sma(")
        )
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    for entry in payload["wire"]:
        messages = _frames(entry["data"])
        for message in messages:
            if message["m"] == "du" and "study" in message["p"][1]:
                rows = message["p"][1]["study"]["st"]
                rows[0]["v"][1] = 1
                rows[1]["v"][1] = 1
                rows[missing_index]["v"][1] = value
        entry["data"] = "".join(_frame(message) for message in messages)
    return source, payload


def parse(source, payload, bindings=BINDINGS):
    return parse_native_capture(
        payload,
        source=source.encode(),
        signal_bindings=bindings,
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={},
    )


@pytest.mark.parametrize("version", [4, 5])
def test_observed_initial_missing_is_preserved_and_known_window_remains_usable(version):
    source, payload = missing_capture(version)
    capture = parse(source, payload)
    first = datetime.fromtimestamp(T0, UTC)
    assert capture.observations.iloc[0]["plot_0"] == 1e100
    assert capture.metadata["missing_alertconditions"] == [
        {"bar_time": first.isoformat(), "column": 1, "direction": "long", "line": 5, "value": 1e100}
    ]
    assert len(capture.events) == 1 and capture.events[0].bar_time == first + timedelta(hours=1)
    with pytest.raises(ValueError, match="미관측"):
        capture.window_events(first, first + timedelta(hours=2))
    assert (
        capture.window_events(first + timedelta(hours=1), first + timedelta(hours=2))
        == capture.events
    )


def test_missing_inside_post_warmup_window_cannot_be_promoted_as_hold():
    source, payload = missing_capture(missing_index=1)
    capture = parse(source, payload)
    first = datetime.fromtimestamp(T0, UTC)
    assert len(capture.window_events(first, first + timedelta(hours=1))) == 1
    with pytest.raises(ValueError, match="미관측"):
        capture.window_events(first + timedelta(hours=1), first + timedelta(hours=2))


@pytest.mark.parametrize(
    "version,value",
    [
        (6, 1e100),
        (3, 1e100),
        (5, None),
        (4, None),
        (5, -1e100),
        (5, 1e99),
        (5, 1e101),
        (5, 2),
        (5, float("nan")),
        (5, float("inf")),
        (5, -float("inf")),
        (5, True),
    ],
)
def test_unobserved_alert_missing_forms_remain_rejected(version, value):
    source, payload = missing_capture(version, value)
    with pytest.raises(ValueError):
        parse(source, payload)


def test_only_reviewed_alert_columns_gain_missing_metadata():
    source, payload = missing_capture()
    capture = parse(
        source, payload, [{"function": "plotshape", "line": 7, "column": 0, "direction": "long"}]
    )
    assert "missing_alertconditions" not in capture.metadata
    first = datetime.fromtimestamp(T0, UTC)
    assert len(capture.window_events(first, first + timedelta(hours=2))) == 1


def test_known_same_bar_long_short_collision_is_still_rejected_after_missing_prefix():
    source, payload = missing_capture()
    source += 'alertcondition(buy,title="Sell",message="S")\n'
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["stats"]["alertcondition"] = 2
    meta["plots"].append({"id": "plot_3", "type": "alertcondition"})
    meta["styles"]["plot_3"] = {"title": "Sell", "text": "S"}
    for entry in payload["wire"]:
        messages = _frames(entry["data"])
        for message in messages:
            if message["m"] == "du" and "study" in message["p"][1]:
                rows = message["p"][1]["study"]["st"]
                rows[0]["v"].append(1e100)
                rows[1]["v"].append(1)
        entry["data"] = "".join(_frame(message) for message in messages)
    with pytest.raises(ValueError, match="충돌"):
        parse(
            source,
            payload,
            [
                *BINDINGS,
                {"function": "alertcondition", "line": 8, "column": 0, "direction": "short"},
            ],
        )

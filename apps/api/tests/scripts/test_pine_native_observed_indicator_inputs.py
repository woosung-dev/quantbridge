"""추가 세 원문에서 관측한 퍼센트 입력·빈 indicator 주기·barcolor 계약만 검증한다."""

import hashlib

import pytest

from scripts.pine_validation.native_capture import _frames, _source_calls
from tests.scripts.test_pine_native_source_resolution import resolution_payload
from tests.scripts.test_pine_validation_native_capture import SOURCE, _frame, _parse, _payload


def set_source(payload, source):
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )


@pytest.mark.parametrize(
    "call,default", [('input.float(2, title="Length")', 2), ('input(50, title="Length")', 50)]
)
def test_percentage_input_keeps_raw_slot_default_instead_of_division_result(call, default):
    source = SOURCE.replace('input.int(2, title="Length")', f"{call} / 100")
    assert _source_calls(source)[1] == [("length", "Length", default)]
    payload = _payload()
    set_source(payload, source)
    payload["resolved_inputs"] = {"length": default}
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["inputs"][1].update(
        defval=default, type="float" if call.startswith("input.float") else "integer"
    )
    message = _frames(payload["wire"][0]["data"])[0]
    message["p"][5]["in_0"]["v"] = default
    payload["wire"][0]["data"] = _frame(message)
    assert len(_parse(payload, source=source).events) == 1


@pytest.mark.parametrize(
    "expression",
    ["input.float(2) / 99", "input.float(2) + 0", "100 / input.float(2)", "input.float(2) / 100.0"],
)
def test_unobserved_input_wrappers_are_not_extracted(expression):
    assert _source_calls(f'//@version=5\nindicator("x")\np = {expression}\n')[1] == []


@pytest.mark.parametrize("value", [True, "2", float("nan")])
@pytest.mark.parametrize("location", ["metadata", "resolved", "wire"])
def test_float_input_does_not_coerce_bool_numeric_string_or_nan(value, location):
    source = SOURCE.replace('input.int(2, title="Length")', 'input.float(2, title="Length") / 100')
    payload = _payload()
    set_source(payload, source)
    metadata = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    metadata["type"] = "float"
    if location == "metadata":
        metadata["defval"] = value
    elif location == "resolved":
        payload["resolved_inputs"]["length"] = value
    else:
        message = _frames(payload["wire"][0]["data"])[0]
        message["p"][5]["in_0"]["v"] = value
        payload["wire"][0]["data"] = _frame(message)
    with pytest.raises(ValueError):
        _parse(payload, source=source)


def indicator_payload():
    source, payload, meta, create = resolution_payload('indicator("demo", timeframe="")')
    meta["inputs"][-1] = {
        "id": "in_1",
        "name": "Timeframe",
        "type": "resolution",
        "group": "Calculation",
        "solutionId": 43000591555,
        "isMTFResolution": True,
        "isFake": True,
        "defval": "",
    }
    return source, payload, meta, create


def test_observed_indicator_timeframe_slot_requires_empty_source_metadata_and_wire():
    source, payload, _, _ = indicator_payload()
    assert len(_parse(payload, source=source).events) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "Other"),
        ("group", "Other"),
        ("solutionId", 0),
        ("type", "text"),
        ("isMTFResolution", 1),
        ("isFake", 1),
        ("defval", "60"),
    ],
)
def test_indicator_auto_slot_rejects_changed_metadata(field, value):
    source, payload, meta, _ = indicator_payload()
    meta["inputs"][-1][field] = value
    with pytest.raises(ValueError, match="resolution"):
        _parse(payload, source=source)


@pytest.mark.parametrize(
    "change",
    [
        "wire_override",
        "wire_flag",
        "wire_type",
        "extra_meta",
        "extra_wire",
        "duplicate",
        "source_mtf",
        "source_absent",
    ],
)
def test_indicator_auto_slot_rejects_override_extra_slot_or_unobserved_source(change):
    source, payload, meta, create = indicator_payload()
    if change == "wire_override":
        create["p"][5]["in_1"]["v"] = "60"
    elif change == "wire_flag":
        create["p"][5]["in_1"]["f"] = 1
    elif change == "wire_type":
        create["p"][5]["in_1"]["t"] = "text"
    elif change == "extra_meta":
        meta["inputs"].append({"id": "in_2", "defval": ""})
    elif change == "extra_wire":
        create["p"][5]["in_2"] = {"v": ""}
    elif change == "duplicate":
        meta["inputs"].append(dict(meta["inputs"][-1]))
    elif change == "source_mtf":
        source = source.replace('timeframe=""', 'timeframe="60"')
    else:
        source = source.replace(', timeframe=""', "")
    set_source(payload, source)
    payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError):
        _parse(payload, source=source)


def barcolor_payload():
    source = SOURCE + "barcolor(color.red)\n"
    payload = _payload()
    set_source(payload, source)
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"].append({"id": "plot_3", "type": "bar_colorer", "palette": "palette_0"})
    meta["styles"]["plot_3"] = {"title": "Bar Color"}
    messages = _frames(payload["wire"][1]["data"])
    for message in messages:
        if message["m"] == "du" and "study" in message["p"][1]:
            for row in message["p"][1]["study"]["st"]:
                row["v"].append(0)
    payload["wire"][1]["data"] = "".join(_frame(message) for message in messages)
    return source, payload, meta


def test_observed_barcolor_column_is_preserved_but_never_a_direction_signal():
    source, payload, _ = barcolor_payload()
    native = _parse(payload, source=source)
    assert native.observations.shape == (2, 4)
    assert len(native.events) == 1 and native.events[0].direction == "long"
    with pytest.raises(ValueError, match="신호"):
        _parse(
            payload,
            source=source,
            bindings=[{"function": "barcolor", "line": 8, "column": 0, "direction": "long"}],
        )


@pytest.mark.parametrize("change", ["source_absent", "type", "title", "order", "wire_width"])
def test_barcolor_requires_original_call_exact_type_title_order_and_wire_width(change):
    source, payload, meta = barcolor_payload()
    if change == "source_absent":
        source = SOURCE
    elif change == "type":
        meta["plots"][-1]["type"] = "line"
    elif change == "title":
        meta["styles"]["plot_3"]["title"] = "Other"
    elif change == "order":
        meta["plots"][1]["type"], meta["plots"][3]["type"] = (
            meta["plots"][3]["type"],
            meta["plots"][1]["type"],
        )
    else:
        messages = _frames(payload["wire"][1]["data"])
        for message in messages:
            if message["m"] == "du" and "study" in message["p"][1]:
                message["p"][1]["study"]["st"][0]["v"].pop()
        payload["wire"][1]["data"] = "".join(_frame(message) for message in messages)
    set_source(payload, source)
    with pytest.raises(ValueError):
        _parse(payload, source=source)


def test_empty_indicator_cannot_reuse_study_specific_compiler_metadata():
    source, payload, _, _ = resolution_payload('indicator("demo", timeframe="")')
    with pytest.raises(ValueError, match="resolution"):
        _parse(payload, source=source)


def test_barcolor_does_not_accept_an_unobserved_custom_title():
    source, payload, meta = barcolor_payload()
    source = source.replace("barcolor(color.red)", 'barcolor(color.red, title="Other")')
    set_source(payload, source)
    meta["styles"]["plot_3"]["title"] = "Other"
    with pytest.raises(ValueError, match="Bar Color"):
        _parse(payload, source=source)


def test_percent_wrapper_does_not_expand_builtin_source_inputs():
    assert _source_calls('//@version=5\nindicator("x")\nsrc = input(close) / 100\n')[1] == []

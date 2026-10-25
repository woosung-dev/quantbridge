"""실측 문자열·색 입력의 source/compiler/wire 계약. 기존 raw fixture는 변경하지 않는다."""

import copy
import hashlib

import pytest

from scripts.pine_validation.native_capture import _frames, _source_calls, parse_native_capture
from tests.scripts.test_pine_validation_native_capture import SOURCE, _frame, _payload

EXTRA = """preset = input.string("Default", "Preset", options=["Default", "Custom"], group="Settings")
bull = input.color(#00ffaa, "Bull", group="Colors")
white = input.color(color.white, "White")
background = input.color(color.new(#1a1a1a, 0), "Background")
"""
# rbeErVR5 native 1h 실제 관측: source cad57079657a7ab8bfe3169df032f6d4c3a456778f316a7f65aa8a4a1a7163c6,
# raw SHA 21f2ae1951312d9774339d81057d7f71bb16f42e55e55f0b0bdf65f1fc2ddb1c.
# 인증정보·IL·원시 브라우저 응답 대신 관측한 입력 스칼라만 재사용한다.
OBSERVED = [
    ("preset", "Preset", "text", "Default", "Default"),
    ("bull", "Bull", "color", "#00ffaa", 4289396480),
    ("white", "White", "color", "#FFFFFF", 4294967295),
    ("background", "Background", "color", "rgba(26,26,26,1)", 4279900698),
]


def payload():
    result = _payload()
    source = SOURCE.replace(
        'length = input.int(2, title="Length")\n', 'length = input.int(2, title="Length")\n' + EXTRA
    )
    result.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = result["compile_responses"][0]["data"]["result"]["metaInfo"]
    create = _frames(result["wire"][0]["data"])[0]
    for index, (name, title, kind, default, wire) in enumerate(OBSERVED, 1):
        meta["inputs"].append({"id": f"in_{index}", "name": title, "type": kind, "defval": default})
        create["p"][5][f"in_{index}"] = {"v": wire, "f": True, "t": kind}
        result["resolved_inputs"][name] = default
    result["wire"][0]["data"] = _frame(create)
    return source, result


def parse(source, result, overrides=None):
    return parse_native_capture(
        result,
        source=source.encode(),
        signal_bindings=[
            {
                "function": "alertcondition",
                "line": 9,
                "column": 0,
                "direction": "long",
                "when": "truthy",
            }
        ],
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs=overrides or {},
    )


def test_observed_string_and_color_defaults_bind_all_slots():
    source, result = payload()
    _, inputs, _ = _source_calls(source)
    assert inputs[1:] == [(name, title, default) for name, title, _, default, _ in OBSERVED]
    assert len(parse(source, result).ohlcv) == 2


@pytest.mark.parametrize(
    "change", ["meta", "wire", "bool", "signed", "source_color", "source_string"]
)
def test_color_or_string_contract_tampering_is_rejected(change):
    source, result = payload()
    meta = result["compile_responses"][0]["data"]["result"]["metaInfo"]
    create = _frames(result["wire"][0]["data"])[0]
    if change == "meta":
        meta["inputs"][3]["defval"] = "#ff0000"
    elif change == "wire":
        create["p"][5]["in_2"]["v"] = 4278190335
    elif change == "bool":
        create["p"][5]["in_2"]["v"] = True
    elif change == "signed":
        create["p"][5]["in_2"]["v"] = 4289396480 - 2**32
    elif change == "source_color":
        result["resolved_inputs"]["bull"] = "#ff0000"
    else:
        result["resolved_inputs"]["preset"] = 1
    result["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError):
        parse(source, result)


def test_override_changes_wire_but_compiler_keeps_source_default():
    source, result = payload()
    result["inputs"] = {"preset": "Custom", "length": 3}
    result["resolved_inputs"].update(result["inputs"])
    create = _frames(result["wire"][0]["data"])[0]
    create["p"][5]["in_0"]["v"] = 3
    create["p"][5]["in_1"]["v"] = "Custom"
    result["wire"][0]["data"] = _frame(create)
    assert len(parse(source, result, result["inputs"]).ohlcv) == 2
    changed = copy.deepcopy(result)
    changed["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][2]["defval"] = "Custom"
    with pytest.raises(ValueError, match="컴파일 입력"):
        parse(source, changed, result["inputs"])


@pytest.mark.parametrize(
    "default",
    [
        "color.new(#1a1a1a,50)",
        "color.rgb(26,26,26)",
        "color.custom",
        '"#ffffff"',
        "make_color()",
    ],
)
def test_unobserved_or_dynamic_color_defaults_remain_unsupported(default):
    with pytest.raises(ValueError):
        _source_calls(f'//@version=6\nindicator("strict")\nx=input.color({default})\n')


def test_input_string_requires_actual_string_literal():
    with pytest.raises(ValueError):
        _source_calls('//@version=6\nindicator("strict")\nx=input.string(1)\n')


def mtf_payload():
    source, result = payload()
    source = source.replace(
        'indicator("demo")', 'indicator("demo",timeframe="",timeframe_gaps=false)'
    )
    result.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = result["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["inputs"] += [
        {
            "active": True,
            "defval": "",
            "group": "Calculation",
            "id": "in_5",
            "isFake": True,
            "isMTFResolution": True,
            "name": "Timeframe",
            "solutionId": 43000591555,
            "type": "resolution",
        },
        {
            "active": True,
            "defval": False,
            "group": "Calculation",
            "id": "in_6",
            "isFake": True,
            "isMTFGaps": True,
            "name": "Wait for timeframe closes",
            "type": "bool",
        },
    ]
    create = _frames(result["wire"][0]["data"])[0]
    create["p"][5].update(
        in_5={"v": "", "f": True, "t": "resolution"}, in_6={"v": False, "f": True, "t": "bool"}
    )
    result["wire"][0]["data"] = _frame(create)
    return source, result


def test_observed_explicit_false_gaps_and_active_resolution_slots():
    source, result = mtf_payload()
    assert len(parse(source, result).ohlcv) == 2


@pytest.mark.parametrize(
    "field,value", [("defval", True), ("defval", 0), ("active", 1), ("isMTFGaps", 1), ("isFake", 1)]
)
def test_mtf_gaps_compiler_slot_is_exact(field, value):
    source, result = mtf_payload()
    result["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][-1][field] = value
    with pytest.raises(ValueError, match="gaps"):
        parse(source, result)


@pytest.mark.parametrize("field,value", [("v", True), ("v", 0), ("f", 1), ("t", "integer")])
def test_mtf_gaps_wire_slot_is_exact(field, value):
    source, result = mtf_payload()
    create = _frames(result["wire"][0]["data"])[0]
    create["p"][5]["in_6"][field] = value
    result["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError, match="gaps"):
        parse(source, result)


def test_tonumber_wrapper_preserves_raw_text_slot_default():
    _, inputs, _ = _source_calls(
        '//@version=6\nindicator("slot")\nbandscale=str.tonumber(input.string("100","Band Scale",options=["100","200"]))\n'
    )
    assert inputs == [("bandscale", "Band Scale", "100")]


@pytest.mark.parametrize("wire", [False, True])
def test_color_slot_cannot_be_downgraded_to_text(wire):
    source, result = payload()
    if wire:
        create = _frames(result["wire"][0]["data"])[0]
        create["p"][5]["in_2"]["t"] = "text"
        result["wire"][0]["data"] = _frame(create)
    else:
        result["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][3]["type"] = "text"
    with pytest.raises(ValueError, match="입력"):
        parse(source, result)


def gradient_binding(source=None, columns=None):
    from scripts.pine_validation.native_capture import _plot_bindings
    from tests.scripts.test_pine_validation_native_capture import BINDINGS

    source = source or SOURCE + "fill(lineHandle,lineHandle,length,4,color.new(fillColor,60),na)\n"
    calls, _, fills = _source_calls(source)
    meta = _payload()["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"] += columns or [
        {"id": "plot_3", "type": "data", "target": "fill_0", "targetField": "topValue"},
        {"id": "plot_4", "type": "colorer", "target": "fill_0", "targetField": "topColor"},
    ]
    return _plot_bindings(calls, meta["plots"], meta["styles"], BINDINGS, fills)


def test_observed_gradient_fill_data_columns_keep_signal_plot_number():
    assert gradient_binding() == [(1, "long", 5)]
    assert gradient_binding(
        SOURCE + "fill(lineHandle,lineHandle,-length,-4,color.new(fillColor,60),na)\n"
    ) == [(1, "long", 5)]


@pytest.mark.parametrize("mutation", ["field", "target", "type", "order", "extra", "missing"])
def test_gradient_fill_columns_are_exact_not_generic_filtered(mutation):
    columns = [
        {"id": "plot_3", "type": "data", "target": "fill_0", "targetField": "topValue"},
        {"id": "plot_4", "type": "colorer", "target": "fill_0", "targetField": "topColor"},
    ]
    if mutation == "field":
        columns[0]["targetField"] = "bottomValue"
    elif mutation == "target":
        columns[0]["target"] = "fill_1"
    elif mutation == "type":
        columns[0]["type"] = "line"
    elif mutation == "order":
        columns[0]["type"], columns[1]["type"] = "colorer", "data"
    elif mutation == "extra":
        columns.append(
            {"id": "plot_5", "type": "data", "target": "fill_0", "targetField": "bottomValue"}
        )
    else:
        columns.pop()
    with pytest.raises(ValueError):
        gradient_binding(columns=columns)


def test_unobserved_gradient_source_shape_remains_unsupported():
    with pytest.raises(ValueError, match="gradient"):
        gradient_binding(
            SOURCE + "fill(lineHandle,lineHandle,length,otherValue,color.new(fillColor,60),na)\n"
        )


def test_legacy_positional_three_argument_fill_is_preserved():
    assert gradient_binding(
        SOURCE + "fill(lineHandle,lineHandle,color.red)\n",
        [{"id": "plot_3", "type": "colorer", "target": "fill_0"}],
    ) == [(1, "long", 5)]


def test_observed_v5_mtf_slots_without_active_field():
    source, result = mtf_payload()
    for slot in result["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][-2:]:
        del slot["active"]
    assert len(parse(source, result).ohlcv) == 2


def test_legacy_regular_fill_palette_metadata_is_preserved():
    assert gradient_binding(
        SOURCE + "fill(lineHandle,lineHandle,color.red)\n",
        [{"id": "plot_3", "type": "colorer", "target": "fill_0", "palette": "palette_1"}],
    ) == [(1, "long", 5)]


@pytest.mark.parametrize("override", [False, True])
def test_integer_resolved_or_override_cannot_be_boolean(override):
    source, result = payload()
    source = source.replace('input.int(2, title="Length")', 'input.int(1, title="Length")')
    result.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    slot = result["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    slot.update(defval=1, type="integer")
    result["resolved_inputs"]["length"] = True
    if override:
        result["inputs"] = {"length": True}
    create = _frames(result["wire"][0]["data"])[0]
    create["p"][5]["in_0"]["v"] = True
    result["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError, match="입력"):
        parse(source, result, result["inputs"])


@pytest.mark.parametrize(
    "kind,actual,expected",
    [
        ("integer", True, 1),
        ("integer", True, True),
        ("bool", 1, True),
        ("bool", 0, 0),
        ("float", True, 1.0),
        ("text", 1, 1),
    ],
)
def test_typed_input_comparison_rejects_boolean_numeric_coercion(kind, actual, expected):
    from scripts.pine_validation.native_capture import _input_equal

    assert not _input_equal(actual, expected, kind)

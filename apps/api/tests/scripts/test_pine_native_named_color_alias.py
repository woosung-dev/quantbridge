"""관측한 generic input의 readonly named-color 별칭만 버전별 SSOT로 연결한다."""

import hashlib

import pytest

from scripts.pine_validation.native_capture import (
    _frames,
    _source_calls,
    _wire_color,
    parse_native_capture,
)
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, _frame, _payload

# wCbldhhg 원문 735b076735746c8c7fae3c3f1f3a26c890f58da4f0cb9a1066d696d994ebfb5e:
# L18 colorTrendNeutral=color.gray → L291 input(defval=colorTrendNeutral).
# 실제 1h raw wrapper SHA 2400393cc1dd764552058c8576e29e2d21435b46ba0cf6ff4ed361f83697bd7e.
# in_17 compiler type=color/defval=#787B86, wire v=#787B86/t=color. 비공개 IL은 복사하지 않는다.


def _source(body, expression="input(neutral, title='Length')", version=5):
    declaration = "study" if version == 4 else "indicator"
    return f'//@version={version}\n{declaration}("alias")\n{body}\nvalue={expression}\n'


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize("name", ["gray", "red", "teal", "yellow"])
@pytest.mark.parametrize("typed", [False, True])
def test_readonly_named_alias_uses_version_aware_color_ssot(version, name, typed):
    expression = "input(neutral, title='Length'" + (", type=input.color)" if typed else ")")
    kinds = {}
    _, inputs, _ = _source_calls(_source(f"neutral=color.{name}", expression, version), input_types=kinds)
    expected = {
        "gray": "#787B86",
        "red": "#F23645" if version == 6 else "#FF5252",
        "teal": "#089981" if version == 6 else "#00897B",
        "yellow": "#FDD835" if version == 6 else "#FFEB3B",
    }[name]
    assert inputs == [("value", "Length", expected)]
    assert kinds == {"value": "color"}


@pytest.mark.parametrize(
    "body",
    [
        "neutral=color.gray\nneutral:=color.red",
        "neutral=color.gray\nneutral+=1",
        "neutral=color.gray\nif close>open\n    neutral:=color.red",
        "neutral=color.gray\nf()=>\n    neutral=color.red\n    neutral",
        "neutral=color.gray\nf(neutral)=>neutral",
        "neutral=color.gray\nneutral()=>color.red",
        "neutral=color.gray\nfor neutral=0 to 1\n    x=neutral",
        "neutral=color.gray\nfor neutral in array.from(1,2)\n    x=neutral",
        "neutral=color.gray\nneutral=color.gray",
        "neutral=close>open?color.gray:color.red",
        "base=color.gray\nneutral=base",
        "neutral=color.new(color.gray,20)",
        "neutral=color.rgb(1,2,3)",
        "neutral=color.unknown",
    ],
)
def test_reassignment_shadow_dynamic_calls_and_alias_chains_remain_rejected(body):
    with pytest.raises(ValueError):
        _source_calls(_source(body))


@pytest.mark.parametrize(
    "expression",
    [
        "input.source(neutral)",
        "input(neutral,type=input.source)",
        "input(neutral,type=input.string)",
        "input.string(neutral)",
        "input(neutral,type=input.integer)",
    ],
)
def test_color_alias_cannot_become_source_text_or_number(expression):
    with pytest.raises(ValueError):
        _source_calls(_source("neutral=color.gray", expression))


def _case(version=5):
    source = SOURCE.replace("//@version=5", f"//@version={version}").replace(
        'length = input.int(2, title="Length")',
        'neutral=color.gray\nlength=input(neutral,title="Length")',
    )
    if version == 4:
        source = source.replace('indicator("demo")', 'study("demo")')
    payload = _payload()
    payload.update(source_sha256=hashlib.sha256(source.encode()).hexdigest(), compiled_source=source, compile_request_source=source, resolved_inputs={"length": "#787B86"})
    slot = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    slot.update(type="color", defval="#787B86", isFake=True)
    create = _frames(payload["wire"][0]["data"])[0]
    create["p"][5]["in_0"] = {"v": _wire_color("#787B86") if version == 6 else "#787B86", "f": True, "t": "color"}
    payload["wire"][0]["data"] = _frame(create)
    return source, payload


def _parse(source, payload):
    return parse_native_capture(payload, source=source.encode(), signal_bindings=[{**binding, "line": binding["line"] + 1} for binding in BINDINGS], expected_indicator_id="example", expected_symbol="BYBIT:BTCUSDT.P", expected_timeframe="1h", expected_inputs={})


@pytest.mark.parametrize("version", [4, 5, 6])
def test_named_alias_compiler_and_wire_contract(version):
    source, payload = _case(version)
    capture = _parse(source, payload)
    assert capture.metadata["resolved_inputs"] == {"length": "#787B86"}
    assert len(capture.events) == 1


@pytest.mark.parametrize("change", ["compiler_type", "compiler_default", "wire_type", "wire_default", "resolved"])
def test_wrong_compiler_wire_or_resolved_color_cannot_pass(change):
    source, payload = _case()
    slot = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    create = _frames(payload["wire"][0]["data"])[0]
    if change == "compiler_type":
        slot["type"] = "text"
    elif change == "compiler_default":
        slot["defval"] = "#787B85"
    elif change == "wire_type":
        create["p"][5]["in_0"]["t"] = "source"
    elif change == "wire_default":
        create["p"][5]["in_0"]["v"] = "#787B85"
    else:
        payload["resolved_inputs"]["length"] = "#787B85"
    payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError):
        _parse(source, payload)


def test_v6_does_not_gain_legacy_string_color_wire_support():
    source, payload = _case(6)
    create = _frames(payload["wire"][0]["data"])[0]
    create["p"][5]["in_0"]["v"] = "#787B86"
    payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError):
        _parse(source, payload)

"""입력의 원시 슬롯을 읽되 바깥 연산·미지 표현식은 평가하지 않는다."""

import hashlib

import pytest

from scripts.pine_validation.native_capture import _frames, _source_calls, parse_native_capture
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, _frame, _payload


@pytest.mark.parametrize(
    "expression,expected",
    [
        ('input.source(volume,"Volume")', [("value", "Volume", "volume")]),
        ('input.int(-25,"Below")', [("value", "Below", -25)]),
        ('input.float(-0.034,"Step")', [("value", "Step", -0.034)]),
        ('input.int(+25,"Above")', [("value", "Above", 25)]),
        ('input.string(size.tiny,"Text")', [("value", "Text", "tiny")]),
        ('11-input.int(7,"Scale")', [("value", "Scale", 7)]),
        ('input.int(3,"Offset")/10', [("value", "Offset", 3)]),
        ('input.float(1.0,"Risk")/100', [("value", "Risk", 1.0)]),
    ],
)
def test_observed_raw_input_default_is_preserved(expression, expected):
    _, inputs, _ = _source_calls(f'//@version=6\nindicator("defaults")\nvalue={expression}\n')
    assert inputs == expected
    assert type(inputs[0][2]) is type(expected[0][2])


@pytest.mark.parametrize(
    "expression",
    [
        'input.int(-true,"Below")',
        'input.string(size.custom,"Text")',
        'input.float(-other,"Step")',
        'input.int(3,"Offset")/unknown',
        'input.int(3,"Offset")/0',
        '11-input.int(7,"A")+input.int(3,"B")',
        'custom(input.int(3,"Offset"))',
    ],
)
def test_unknown_input_expression_is_not_evaluated_or_silently_omitted(expression):
    with pytest.raises(ValueError):
        _source_calls(f'//@version=6\nindicator("defaults")\nvalue={expression}\n')


@pytest.mark.parametrize(
    "expression,raw_default,calculated",
    [
        ('11-input.int(7,title="Length")', 7, 4),
        ('input.int(3,title="Length")/10', 3, 0.3),
        ('input.float(1.0,title="Length")/100', 1.0, 0.01),
        ('input.int(-25,title="Length")', -25, 25),
    ],
)
def test_compiler_and_wire_must_match_raw_slot_not_outer_result(
    expression, raw_default, calculated
):
    source = SOURCE.replace('input.int(2, title="Length")', expression)
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
        resolved_inputs={"length": raw_default},
    )
    slot = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    slot.update(defval=raw_default, type="integer" if type(raw_default) is int else "float")
    create = _frames(payload["wire"][0]["data"])[0]
    create["p"][5]["in_0"]["v"] = raw_default
    payload["wire"][0]["data"] = _frame(create)

    def parse():
        return parse_native_capture(
            payload,
            source=source.encode(),
            signal_bindings=BINDINGS,
            expected_indicator_id="example",
            expected_symbol="BYBIT:BTCUSDT.P",
            expected_timeframe="1h",
            expected_inputs={},
        )

    assert len(parse().events) == 1
    create["p"][5]["in_0"]["v"] = calculated
    payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError, match="실제 입력"):
        parse()


# native184/186/187의 실제 compiler defval·typed wire 관측이다.
# 원시 HTTP/IL/인증정보는 저장하지 않는다.
COLOR_OBSERVATIONS = [
    (5, "color.green", "#4CAF50", "#4CAF50"),
    (5, "color.red", "#FF5252", "#FF5252"),
    (5, "color.black", "#363A45", "#363A45"),
    (6, "color.aqua", "#00BCD4", 4292131840),
    (6, "color.orange", "#FF9800", 4278229247),
    (6, "color.new(color.aqua,80)", "rgba(0,188,212,0.2)", 869579776),
    (6, "color.new(color.orange,80)", "rgba(255,152,0,0.2)", 855677183),
    (6, "color.lime", "#00E676", 4285982208),
    (6, "color.red", "#F23645", 4282726130),
    (5, "color.new(color.green,70)", "rgba(76,175,80,0.3)", "rgba(76,175,80,0.3)"),
    (5, "color.new(color.red,70)", "rgba(255,82,82,0.3)", "rgba(255,82,82,0.3)"),
]


@pytest.mark.parametrize("version,expression,default,wire", COLOR_OBSERVATIONS)
def test_observed_color_defaults_match_version_and_actual_wire(version, expression, default, wire):
    source = SOURCE.replace("//@version=5", f"//@version={version}").replace(
        'input.int(2, title="Length")', f'input.color({expression}, title="Length")'
    )
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
        resolved_inputs={"length": default},
    )
    slot = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    slot.update(type="color", defval=default)
    create = _frames(payload["wire"][0]["data"])[0]
    create["p"][5]["in_0"].update(t="color", v=wire)
    payload["wire"][0]["data"] = _frame(create)

    def parse():
        return parse_native_capture(
            payload,
            source=source.encode(),
            signal_bindings=BINDINGS,
            expected_indicator_id="example",
            expected_symbol="BYBIT:BTCUSDT.P",
            expected_timeframe="1h",
            expected_inputs={},
        )

    assert len(parse().events) == 1
    create["p"][5]["in_0"]["t"] = "text"
    payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError, match="실제 입력"):
        parse()

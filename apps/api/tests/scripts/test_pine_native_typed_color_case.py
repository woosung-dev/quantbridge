"""실제 blue typed 입력의 hex6 채널 동치만 허용하고 원시 문자열은 보존한다."""

import hashlib

import pytest

from scripts.pine_validation.native_capture import _frames, parse_native_capture
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, _frame, _payload


def blue_case():
    source = SOURCE.replace("//@version=5", "//@version=6").replace(
        'input.int(2, title="Length")', 'input.color(color.blue, title="Length")'
    )
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
        resolved_inputs={"length": "#2962ff"},
    )
    payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1].update(
        type="color", defval="#2962ff"
    )
    create = _frames(payload["wire"][0]["data"])[0]
    create["p"][5]["in_0"].update(v=4294926889, t="color")
    payload["wire"][0]["data"] = _frame(create)
    return source, payload


def parse(source, payload):
    return parse_native_capture(
        payload,
        source=source.encode(),
        signal_bindings=BINDINGS,
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={},
    )


def test_actual_blue_case_retains_original_and_compiler_representation():
    source, payload = blue_case()
    capture = parse(source, payload)
    assert "color.blue" in source
    assert capture.metadata["resolved_inputs"]["length"] == "#2962ff"
    assert (
        payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]["defval"]
        == "#2962ff"
    )
    assert len(capture.events) == 1


@pytest.mark.parametrize(
    "change", ["kind", "titlecase", "channel", "alpha", "unknownhex", "wirebyte"]
)
def test_hex_case_equivalence_cannot_hide_wrong_kind_title_channel_or_alpha(change):
    source, payload = blue_case()
    slot = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    if change == "kind":
        slot["type"] = "text"
    elif change == "titlecase":
        slot["name"] = "length"
    elif change == "channel":
        slot["defval"] = "#2962fe"
    elif change == "alpha":
        slot["defval"] = "#2962ff80"
    elif change == "unknownhex":
        slot["defval"] = "#2962gg"
    else:
        create = _frames(payload["wire"][0]["data"])[0]
        create["p"][5]["in_0"]["v"] -= 1
        payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError):
        parse(source, payload)


@pytest.mark.parametrize("title", ["Long Bars", "Short Bars"])
def test_actual_barcolor_literal_titles_are_compared_exactly(title):
    from tests.scripts.test_pine_native_observed_indicator_inputs import (
        _parse,
        barcolor_payload,
        set_source,
    )

    source, payload, meta = barcolor_payload()
    source = source.replace("barcolor(color.red)", f'barcolor(color.red,title="{title}")')
    set_source(payload, source)
    meta["styles"]["plot_3"]["title"] = title
    assert len(_parse(payload, source=source).events) == 1
    meta["styles"]["plot_3"]["title"] = title.lower()
    with pytest.raises(ValueError, match="제목"):
        _parse(payload, source=source)


def test_actual_bgcolor_keyword_title_is_compared_exactly():
    from tests.scripts.test_pine_native_observed_indicator_inputs import set_source
    from tests.scripts.test_pine_native_static_fill import bg_capture
    from tests.scripts.test_pine_native_static_fill import parse as parse_bg

    source, payload, bindings = bg_capture()
    title = "BG color for positive or negative deviation"
    source = source.replace(
        "bgcolor(buy ? color.green : na)",
        f'bgcolor(title="{title}",color=buy ? color.green : na,transp=70)',
    )
    set_source(payload, source)
    style = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["styles"]["plot_0"]
    style["title"] = title
    assert len(parse_bg(source, payload, bindings).events) == 1
    style["title"] = title.lower()
    with pytest.raises(ValueError, match="제목"):
        parse_bg(source, payload, bindings)


def legacy_hex_case(version):
    from tests.scripts.test_pine_native_input_string_color import payload
    from tests.scripts.test_pine_native_observed_indicator_inputs import set_source

    source, result = payload()
    source = source.replace("//@version=6", f"//@version={version}").replace(
        "//@version=5", f"//@version={version}"
    )
    set_source(result, source)
    result["resolved_inputs"]["bull"] = "#00FFAA"
    create = _frames(result["wire"][0]["data"])[0]
    create["p"][5]["in_2"]["v"] = "#00ffaa"
    result["wire"][0]["data"] = _frame(create)
    return source, result


@pytest.mark.parametrize("version", [4, 5])
def test_legacy_hex6_string_wire_preserves_all_three_representations(version):
    from tests.scripts.test_pine_native_input_string_color import parse as parse_legacy

    source, result = legacy_hex_case(version)
    assert len(parse_legacy(source, result).ohlcv) == 2
    assert result["resolved_inputs"]["bull"] == "#00FFAA"
    assert (
        next(
            item["defval"]
            for item in result["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"]
            if item["id"] == "in_2"
        )
        == "#00ffaa"
    )
    assert _frames(result["wire"][0]["data"])[0]["p"][5]["in_2"]["v"] == "#00ffaa"


@pytest.mark.parametrize("version", [4, 5])
@pytest.mark.parametrize("change", ["channel", "type", "rgba", "text"])
def test_legacy_hex6_wire_equivalence_does_not_widen_other_values(version, change):
    from tests.scripts.test_pine_native_input_string_color import parse as parse_legacy

    source, result = legacy_hex_case(version)
    create = _frames(result["wire"][0]["data"])[0]
    if change == "channel":
        create["p"][5]["in_2"]["v"] = "#00ffab"
    elif change == "type":
        create["p"][5]["in_2"]["t"] = "text"
    elif change == "rgba":
        create["p"][5]["in_4"]["v"] = "rgba(26,26,26,1.0)"
    else:
        create["p"][5]["in_1"]["v"] = "default"
    result["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError, match="create_study"):
        parse_legacy(source, result)

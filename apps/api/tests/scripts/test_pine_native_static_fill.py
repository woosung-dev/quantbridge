"""실제 정적 fill 메타데이터는 색 열 없이 원문 plot 끝점과 결박된다."""

import hashlib
import pickle

import pytest

from scripts.pine_validation.native_capture import (
    _frames,
    _plot_bindings,
    _source_calls,
    _source_plot_variables,
    parse_native_capture,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, _frame, _payload


def capture():
    source = SOURCE.replace('plot(close, title="Line")', 'p2 = plot(close, title="Line")')
    source += 'p3 = plot(open, title="Other")\nfill(p2, p3, color=color.new(#69359C, 70), title="Lag Shading")\n'
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"].append({"id": "plot_3", "type": "line"})
    meta["styles"]["plot_3"] = {"title": "Other"}
    meta["stats"]["plot"] = 2
    meta["filledAreas"] = [
        {
            "id": "fill_0",
            "objAId": "plot_1",
            "objBId": "plot_3",
            "title": "Lag Shading",
            "type": "plot_plot",
            "fillgaps": False,
            "isHidden": False,
        }
    ]
    meta["defaults"] = {
        "filledAreasStyle": {"fill_0": {"color": "rgba(105,53,156,0.3)", "visible": True}}
    }
    for entry in payload["wire"]:
        messages = _frames(entry["data"])
        for message in messages:
            if message["m"] == "du" and "study" in message["p"][1]:
                for row in message["p"][1]["study"]["st"]:
                    row["v"].append(100)
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


def test_observed_static_fill_has_no_colorer_and_preserves_signal_event_column():
    source, payload = capture()
    result = parse(source, payload)
    assert len(result.events) == 1
    assert result.events[0].direction == "long"


def binding_case(two_static=False):
    source = """//@version=6
indicator("fills")
p2 = plot(close, title="A")
p3 = plot(open, title="B")
fill(p2, p3, color=color.new(#69359C, 70), title="Lag Shading")
fill(p2, p3, color=close>open ? color.green : color.red, title="Kalman fill")
alertcondition(close>open, title="Buy")
"""
    if two_static:
        source = source.replace(
            'color=close>open ? color.green : color.red, title="Kalman fill"',
            'color=color.new(#69359C, 70), title="Lag Shading", display=display.none',
        )
    calls, _, fills = _source_calls(source)
    plots = [{"id": "plot_0", "type": "line"}, {"id": "plot_1", "type": "line"}]
    if not two_static:
        plots.append(
            {"id": "plot_2", "type": "colorer", "target": "fill_1", "palette": "palette_0"}
        )
    alert_id = f"plot_{len(plots)}"
    plots.append({"id": alert_id, "type": "alertcondition"})
    areas = [
        {
            "id": f"fill_{i}",
            "objAId": "plot_0",
            "objBId": "plot_1",
            "title": "Lag Shading" if i == 0 or two_static else "Kalman fill",
            "type": "plot_plot",
            "fillgaps": False,
            "isHidden": False,
        }
        for i in range(2)
    ]
    if not two_static:
        areas[1]["palette"] = "palette_0"
    return (
        source,
        calls,
        fills,
        {
            "plots": plots,
            "styles": {
                "plot_0": {"title": "A"},
                "plot_1": {"title": "B"},
                alert_id: {"title": "Buy"},
            },
            "filled_areas": areas,
            "filled_area_defaults": {
                f"fill_{i}": {"color": "rgba(105,53,156,0.3)", "visible": i == 0} for i in range(2)
            },
        },
    )


def bind(source, calls, fills, meta):
    reviewed = [
        {
            "function": "alertcondition",
            "line": calls[-1][1].lineno,
            "column": calls[-1][1].col_offset,
            "direction": "long",
        }
    ]
    return _plot_bindings(
        calls,
        meta["plots"],
        meta["styles"],
        reviewed,
        fills,
        source_plot_variables=_source_plot_variables(source),
        filled_areas=meta["filled_areas"],
        filled_area_defaults=meta["filled_area_defaults"],
    )


@pytest.mark.parametrize("two_static,column", [(False, 4), (True, 3)])
def test_observed_mixed_and_two_static_fills_keep_later_signal_column(two_static, column):
    source, calls, fills, meta = binding_case(two_static)
    assert bind(source, calls, fills, meta) == [(column, "long", 7)]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_area",
        "area_id",
        "endpoint_a",
        "endpoint_b",
        "title",
        "type",
        "fillgaps",
        "hidden",
        "static_palette",
        "missing_style",
        "color",
        "alpha",
        "visible",
        "unknown_style",
        "missing_dynamic",
        "wrong_dynamic_target",
    ],
)
def test_static_metadata_tamper_or_dynamic_column_loss_is_rejected(mutation):
    source, calls, fills, meta = binding_case()
    area = meta["filled_areas"][0]
    style = meta["filled_area_defaults"]["fill_0"]
    if mutation == "missing_area":
        meta["filled_areas"].pop(0)
    elif mutation == "area_id":
        area["id"] = "fill_1"
    elif mutation == "endpoint_a":
        area["objAId"] = "plot_1"
    elif mutation == "endpoint_b":
        area["objBId"] = "plot_3"
    elif mutation == "title":
        area["title"] = "other"
    elif mutation == "type":
        area["type"] = "hline_hline"
    elif mutation == "fillgaps":
        area["fillgaps"] = 0
    elif mutation == "hidden":
        area["isHidden"] = 0
    elif mutation == "static_palette":
        area["palette"] = "palette_0"
    elif mutation == "missing_style":
        del meta["filled_area_defaults"]["fill_0"]
    elif mutation == "color":
        style["color"] = "rgba(106,53,156,0.3)"
    elif mutation == "alpha":
        style["color"] = "rgba(105,53,156,0.7)"
    elif mutation == "visible":
        style["visible"] = 1
    elif mutation == "unknown_style":
        style["width"] = 1
    elif mutation == "missing_dynamic":
        meta["plots"].pop(2)
        meta["plots"][-1]["id"] = "plot_2"
        meta["styles"]["plot_2"] = meta["styles"].pop("plot_3")
    else:
        meta["plots"][2]["target"] = "fill_0"
    with pytest.raises(ValueError):
        bind(source, calls, fills, meta)


@pytest.mark.parametrize(
    "replacement",
    [
        "color.new(#69359C80,70)",
        "color.new(#69359C,transparency)",
        "color.new(color=#69359C,transp=70)",
        "#69359C",
    ],
)
def test_unobserved_static_color_constructor_remains_rejected(replacement):
    source, _, _, meta = binding_case()
    source = source.replace("color.new(#69359C, 70)", replacement)
    calls, _, fills = _source_calls(source)
    with pytest.raises(ValueError):
        bind(source, calls, fills, meta)


def test_plot_handle_reassignment_is_not_guessed_and_cached_ast_is_unchanged():
    source, calls, fills, meta = binding_case()
    tree = parse_to_ast(source)
    before = pickle.dumps(tree)
    assert _source_plot_variables(source) == {"p2": (3, 5), "p3": (4, 5)}
    assert pickle.dumps(tree) == before
    source += "p2 := p3\n"
    calls, _, fills = _source_calls(source)
    with pytest.raises(ValueError, match="끝점"):
        bind(source, calls, fills, meta)


def bg_capture():
    source = SOURCE.replace(
        "alertcondition(buy", "bgcolor(buy ? color.green : na)\nalertcondition(buy"
    )
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"] = [
        {"id": "plot_0", "type": "bg_colorer"},
        {"id": "plot_1", "type": "alertcondition"},
        {"id": "plot_2", "type": "line"},
        {"id": "plot_3", "type": "shapes"},
    ]
    meta["styles"] = {
        "plot_0": {"title": "Background Color", "isHidden": False},
        **{f"plot_{int(key.split('_')[1]) + 1}": style for key, style in meta["styles"].items()},
    }
    for entry in payload["wire"]:
        messages = _frames(entry["data"])
        for message in messages:
            if message["m"] == "du" and "study" in message["p"][1]:
                for row in message["p"][1]["study"]["st"]:
                    row["v"].insert(1, 4289774818)
        entry["data"] = "".join(_frame(message) for message in messages)
    return source, payload, [{**BINDINGS[0], "line": 6}]


def test_observed_bgcolor_is_non_signal_column_not_counted_by_compiler_stats():
    source, payload, bindings = bg_capture()
    result = parse(source, payload, bindings)
    assert len(result.events) == 1 and result.events[0].direction == "long"


@pytest.mark.parametrize(
    "mutation", ["title", "hidden", "extra_style", "type", "missing", "reviewed_entry"]
)
def test_bgcolor_metadata_cannot_shift_or_become_entry_signal(mutation):
    source, payload, bindings = bg_capture()
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    if mutation == "title":
        meta["styles"]["plot_0"]["title"] = "Bar Color"
    elif mutation == "hidden":
        meta["styles"]["plot_0"]["isHidden"] = 0
    elif mutation == "extra_style":
        meta["styles"]["plot_0"]["custom"] = True
    elif mutation == "type":
        meta["plots"][0]["type"] = "bar_colorer"
    elif mutation == "missing":
        del meta["styles"]["plot_0"]
    else:
        bindings = [{"function": "bgcolor", "line": 5, "column": 0, "direction": "long"}]
    with pytest.raises(ValueError):
        parse(source, payload, bindings)

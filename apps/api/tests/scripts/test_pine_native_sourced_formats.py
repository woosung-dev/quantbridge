"""새 원시에서 확인한 비신호 렌더 열·상수·band·typed colour 형식만 검증한다."""

import pytest

from scripts.pine_validation.native_capture import (
    _input_equal,
    _plot_bindings,
    _readonly_globals,
    _source_calls,
    _source_hlines,
    _source_plot_variables,
    _source_static_colors,
)
from src.strategy.pine_v2.interpreter import pine_version_from_ast
from src.strategy.pine_v2.parser_adapter import parse_to_ast


def bind(source, meta, reviewed=None):
    calls, _, fills = _source_calls(source)
    alert = next(call for kind, call in reversed(calls) if kind == "alertcondition")
    return _plot_bindings(
        calls,
        meta["plots"],
        meta["styles"],
        reviewed
        or [
            {
                "function": "alertcondition",
                "line": alert.lineno,
                "column": alert.col_offset,
                "direction": "long",
            }
        ],
        fills,
        source_plot_variables=_source_plot_variables(source),
        source_static_colors=_source_static_colors(source),
        constants=_readonly_globals(source),
        source_version=pine_version_from_ast(parse_to_ast(source)),
        hlines=_source_hlines(source),
        bands=meta.get("bands"),
        band_defaults=meta.get("band_defaults"),
        filled_areas=meta.get("areas"),
        filled_area_defaults=meta.get("defaults"),
    )


def arrow_case():
    return (
        """//@version=6
indicator("arrows")
plotarrow(close-open,title="Momentum Acceleration",colorup=color.green,colordown=color.red)
alertcondition(close>open,title="Long")
""",
        {
            "plots": [
                {"id": "plot_0", "type": "arrows"},
                {"id": "plot_1", "type": "up_colorer", "target": "plot_0"},
                {"id": "plot_2", "type": "down_colorer", "target": "plot_0"},
                {"id": "plot_3", "type": "alertcondition"},
            ],
            "styles": {
                "plot_0": {
                    "isHidden": False,
                    "maxHeight": 100,
                    "minHeight": 5,
                    "title": "Momentum Acceleration",
                },
                "plot_3": {"title": "Long"},
            },
        },
    )


def test_observed_arrow_three_columns_preserve_later_signal_column():
    assert bind(*arrow_case()) == [(4, "long", 4)]


@pytest.mark.parametrize("change", ["target", "order", "palette", "title", "height", "entry"])
def test_arrow_group_is_exact_and_never_an_entry(change):
    source, meta = arrow_case()
    reviewed = None
    if change == "target":
        meta["plots"][1]["target"] = "plot_1"
    elif change == "order":
        meta["plots"][1]["type"], meta["plots"][2]["type"] = (
            meta["plots"][2]["type"],
            meta["plots"][1]["type"],
        )
    elif change == "palette":
        meta["plots"][1]["palette"] = "palette_0"
    elif change == "title":
        meta["styles"]["plot_0"]["title"] = "Other"
    elif change == "height":
        meta["styles"]["plot_0"]["minHeight"] = 5.0
    else:
        reviewed = [{"function": "plotarrow", "line": 3, "column": 0, "direction": "long"}]
    with pytest.raises(ValueError):
        bind(source, meta, reviewed)


def fill_case(kind):
    if kind == "legacy":
        source = """//@version=4
study("legacy")
p1=plot(close,title="A")
p2=plot(open,title="B")
fill(p1,p2,color=color.red,transp=70)
alertcondition(close>open,title="Long")
"""
        color = "#FF5252"
        extra = {"display": 15, "transparency": 70}
    else:
        source = """//@version=5
indicator("constant")
COL_NEUT=#3c94b8
plt_color=close>open?color.red:color.green
p1=plot(close,title="A")
p2=plot(open,title="B")
fill(p1,p2,color=color.new(COL_NEUT,90))
fill(p1,p2,color=plt_color)
alertcondition(close>open,title="Long")
"""
        color = "rgba(60,148,184,0.1)"
        extra = {"transparency": 0}
    plots = [{"id": "plot_0", "type": "line"}, {"id": "plot_1", "type": "line"}]
    areas = [
        {
            "id": "fill_0",
            "objAId": "plot_0",
            "objBId": "plot_1",
            "title": "Plots Background",
            "type": "plot_plot",
            "fillgaps": False,
            "isHidden": False,
        }
    ]
    if kind != "legacy":
        plots.append(
            {"id": "plot_2", "type": "colorer", "target": "fill_1", "palette": "palette_0"}
        )
        areas.append({**areas[0], "id": "fill_1", "palette": "palette_0"})
    alert = f"plot_{len(plots)}"
    plots.append({"id": alert, "type": "alertcondition"})
    return source, {
        "plots": plots,
        "styles": {"plot_0": {"title": "A"}, "plot_1": {"title": "B"}, alert: {"title": "Long"}},
        "areas": areas,
        "defaults": {"fill_0": {"color": color, "visible": True, **extra}},
    }


@pytest.mark.parametrize("kind,column,line", [("legacy", 3, 6), ("hex", 4, 9)])
def test_observed_legacy_and_readonly_hex_fill_preserve_dynamic_columns(kind, column, line):
    assert bind(*fill_case(kind)) == [(column, "long", line)]


@pytest.mark.parametrize(
    "change", ["alpha", "missing_dynamic", "nested_reassign", "nested_augassign", "input"]
)
def test_hex_fill_cannot_guess_mutable_or_input_values(change):
    source, meta = fill_case("hex")
    if change == "alpha":
        meta["defaults"]["fill_0"]["color"] = "rgba(60,148,184,0.2)"
    elif change == "missing_dynamic":
        meta["plots"][2]["target"] = "fill_0"
    elif change == "nested_reassign":
        source += "if barstate.islast\n    COL_NEUT:=#ffffff\n"
    elif change == "nested_augassign":
        source += "if barstate.islast\n    COL_NEUT+=1\n"
    else:
        source = source.replace("COL_NEUT=#3c94b8", "COL_NEUT=input.color(#3c94b8)")
    with pytest.raises(ValueError):
        bind(source, meta)


def rgb_case():
    values = (70, 75, 80, 83, 86, 89, 92, 95, 98, 99)
    source = """//@version=6
indicator("rgb")
bull_color=color.rgb(0,241,255)
bear_color=color.rgb(255,1,154)
p1=plot(close,title="A")
p2=plot(open,title="B")
"""
    areas = []
    defaults = {}
    for i in range(20):
        source += f"fill(p1,p2,color=color.new({'bull_color' if i < 10 else 'bear_color'},{values[i % 10]}))\n"
        target = f"fill_{i}"
        r, g, b = (0, 241, 255) if i < 10 else (255, 1, 154)
        # 실제20개alpha를그대로기대한값이며 source식/전략을실행하지않는다.
        alpha = ("0.3", "0.25", "0.2", "0.17", "0.14", "0.11", "0.08", "0.05", "0.02", "0.01")[
            i % 10
        ]
        areas.append(
            {
                "id": target,
                "objAId": "plot_0",
                "objBId": "plot_1",
                "title": "Plots Background",
                "type": "plot_plot",
                "fillgaps": False,
                "isHidden": False,
            }
        )
        defaults[target] = {"color": f"rgba({r},{g},{b},{alpha})", "visible": True}
    source += 'alertcondition(close>open,title="Long")\n'
    return source, {
        "plots": [
            {"id": "plot_0", "type": "line"},
            {"id": "plot_1", "type": "line"},
            {"id": "plot_2", "type": "alertcondition"},
        ],
        "styles": {"plot_0": {"title": "A"}, "plot_1": {"title": "B"}, "plot_2": {"title": "Long"}},
        "areas": areas,
        "defaults": defaults,
    }


def test_observed_twenty_rgb_constant_fills_add_no_wire_columns():
    assert bind(*rgb_case()) == [(3, "long", 27)]


@pytest.mark.parametrize("change", ["rgb_float", "rgb_extra", "mutable", "rgba"])
def test_rgb_constant_is_only_three_integer_channels_and_never_mutable(change):
    source, meta = rgb_case()
    if change == "rgb_float":
        source = source.replace("rgb(0,241,255)", "rgb(0.0,241,255)")
    elif change == "rgb_extra":
        source = source.replace("rgb(0,241,255)", "rgb(0,241,255,0)")
    elif change == "mutable":
        source += "if barstate.islast\n    bull_color:=color.red\n"
    else:
        meta["defaults"]["fill_19"]["color"] = "rgba(255,1,154,0.02)"
    with pytest.raises(ValueError):
        bind(source, meta)


def hline_case():
    source = """//@version=6
indicator("bands")
p1=hline(75,title="Upper",color=color.red,linestyle=hline.style_dotted)
p2=hline(65,title="Lower",color=color.red,linestyle=hline.style_dotted)
hline(50,title="Mid",color=color.gray,linestyle=hline.style_dotted,linewidth=2)
p3=hline(35,title="LowUpper",color=color.teal,linestyle=hline.style_dotted)
p4=hline(25,title="LowLower",color=color.teal,linestyle=hline.style_dotted)
fill(p1,p2,color=color.new(color.red,89),title="Upper zone")
fill(p3,p4,color=color.new(color.teal,89),title="Lower zone")
alertcondition(close>open,title="Long")
"""
    bands = [
        {"id": f"hline_{i}", "isHidden": False, "name": title}
        for i, title in enumerate(("Upper", "Lower", "Mid", "LowUpper", "LowLower"))
    ]
    defaults = [
        {
            "color": color,
            "linestyle": 1,
            "linewidth": 2 if i == 2 else 1,
            "value": value,
            "visible": True,
        }
        for i, (color, value) in enumerate(
            zip(
                ("#F23645", "#F23645", "#787B86", "#089981", "#089981"),
                (75, 65, 50, 35, 25),
                strict=True,
            )
        )
    ]
    areas = [
        {
            "id": f"fill_{i}",
            "objAId": f"hline_{0 if i == 0 else 3}",
            "objBId": f"hline_{1 if i == 0 else 4}",
            "title": "Upper zone" if i == 0 else "Lower zone",
            "type": "hline_hline",
            "fillgaps": False,
            "isHidden": False,
        }
        for i in range(2)
    ]
    return source, {
        "plots": [{"id": "plot_0", "type": "alertcondition"}],
        "styles": {"plot_0": {"title": "Long"}},
        "bands": bands,
        "band_defaults": defaults,
        "areas": areas,
        "defaults": {
            "fill_0": {"color": "rgba(242,54,69,0.11)", "visible": True},
            "fill_1": {"color": "rgba(8,153,129,0.11)", "visible": True},
        },
    }


def test_hline_ordinals_are_independent_from_plot_ordinals():
    assert bind(*hline_case()) == [(1, "long", 10)]


@pytest.mark.parametrize(
    "change",
    [
        "plot_ordinal",
        "kind",
        "price",
        "unused_mid_price",
        "band_title",
        "band_color",
        "band_width",
        "missing_band",
        "nested_write",
    ],
)
def test_hline_endpoints_and_every_band_are_exact(change):
    source, meta = hline_case()
    if change == "plot_ordinal":
        meta["areas"][0]["objAId"] = "plot_0"
    elif change == "kind":
        meta["areas"][0]["type"] = "plot_plot"
    elif change == "price":
        meta["band_defaults"][0]["value"] = 74
    elif change == "unused_mid_price":
        meta["band_defaults"][2]["value"] = 49
    elif change == "band_title":
        meta["bands"][0]["name"] = "Other"
    elif change == "band_color":
        meta["band_defaults"][0]["color"] = "#FF5252"
    elif change == "band_width":
        meta["band_defaults"][2]["linewidth"] = True
    elif change == "missing_band":
        meta["bands"].pop(2)
    else:
        source += "if barstate.islast\n    p1:=p2\n"
    with pytest.raises(ValueError):
        bind(source, meta)


def test_generic_readonly_hex_input_is_color_and_never_an_ohlc_source():
    source = """//@version=4
study("inputs")
chm1=#ff0000
c=input(chm1,title="Colour")
v=input(volume,title="Volume",type=input.source)
"""
    kinds = {}
    _, inputs, _ = _source_calls(source, input_types=kinds)
    assert inputs == [("c", "Colour", "#ff0000"), ("v", "Volume", "volume")]
    assert kinds == {"c": "color"}
    for suffix in ("if barstate.islast\n    chm1:=#ffffff\n", "if barstate.islast\n    chm1+=1\n"):
        with pytest.raises(ValueError):
            _source_calls(source + suffix)
    with pytest.raises(ValueError):
        _source_calls(
            source.replace(
                'input(chm1,title="Colour")', 'input(chm1,title="Colour",type=input.source)'
            )
        )


@pytest.mark.parametrize(
    "actual,expected,kind,match",
    [
        ("#2962ff", "#2962FF", "color", True),
        ("#2962fe", "#2962FF", "color", False),
        ("#2962ff80", "#2962FF80", "color", False),
        ("#gggggg", "#gggggg", "color", False),
        ("rgba(1,2,3,0.3)", "rgba(1,2,3,0.30)", "color", False),
        ("Tiny", "tiny", "text", False),
        ("CLOSE", "close", "source", False),
    ],
)
def test_only_typed_hex6_color_case_can_be_equivalent(actual, expected, kind, match):
    assert _input_equal(actual, expected, kind) is match

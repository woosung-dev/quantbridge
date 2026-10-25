"""관측한 v4 named fill의 생략 transp=90만 정적 열로 분리한다."""

import pytest

from tests.scripts.test_pine_native_sourced_formats import bind

# 8OVkDNNf 1h 실제 wrapper SHA ddae23ac85ba075d8c91d43ba96dc1a95f330f91a898d9b61c0edeb26ecc7d01.
# 실제 fill_0 color=#FFEB3B/display15/transparency90/visibletrue, 뒤 fill_1/2만 colorer다.
# 원문·IL·신호값 대신 해당 source/meta 형식만 작은 신뢰 fixture로 재현한다.


def case():
    source = """//@version=4
study("defaults")
pc=plot(close,title="C")
p1=plot(high,title="A")
p2=plot(low,title="B")
fill(p1,p2,color=color.yellow)
fill(pc,p1,color=close>open?color.green:na)
fill(pc,p2,color=close<open?color.red:na)
alertcondition(close>open,title="Long")
"""
    areas = [
        {"id": f"fill_{i}", "objAId": left, "objBId": right, "title": "Plots Background", "type": "plot_plot", "fillgaps": False, "isHidden": False, **({"palette": f"palette_{i-1}"} if i else {})}
        for i, (left, right) in enumerate([("plot_1", "plot_2"), ("plot_0", "plot_1"), ("plot_0", "plot_2")])
    ]
    return source, {
        "plots": [
            {"id": "plot_0", "type": "line"},
            {"id": "plot_1", "type": "line"},
            {"id": "plot_2", "type": "line"},
            {"id": "plot_3", "type": "colorer", "target": "fill_1", "palette": "palette_0"},
            {"id": "plot_4", "type": "colorer", "target": "fill_2", "palette": "palette_1"},
            {"id": "plot_5", "type": "alertcondition"},
        ],
        "styles": {"plot_0": {"title": "C"}, "plot_1": {"title": "A"}, "plot_2": {"title": "B"}, "plot_5": {"title": "Long"}},
        "areas": areas,
        "defaults": {f"fill_{i}": {"color": "#2196F3" if i else "#FFEB3B", "display": 15, "transparency": 90, "visible": True} for i in range(3)},
    }


def test_v4_omitted_transparency_has_no_static_colorer_and_keeps_dynamic_order():
    assert bind(*case()) == [(6, "long", 9)]


@pytest.mark.parametrize(
    "change",
    ["endpoint", "order", "area_missing", "palette_on_static", "title", "area_type", "hidden", "fillgaps", "style_missing", "color", "transparency", "transparency_float", "display", "display_float", "visible_false", "visible_number", "unknown_style", "dynamic_target", "dynamic_order", "dynamic_missing"],
)
def test_observed_static_defaults_endpoints_and_dynamic_columns_remain_exact(change):
    source, meta = case()
    area = meta["areas"][0]
    style = meta["defaults"]["fill_0"]
    if change == "endpoint":
        area["objAId"] = "plot_0"
    elif change == "order":
        meta["areas"][0], meta["areas"][1] = meta["areas"][1], meta["areas"][0]
    elif change == "area_missing":
        meta["areas"].pop()
    elif change == "palette_on_static":
        area["palette"] = "palette_0"
    elif change == "title":
        area["title"] = "Other"
    elif change == "area_type":
        area["type"] = "hline_hline"
    elif change == "hidden":
        area["isHidden"] = 0
    elif change == "fillgaps":
        area["fillgaps"] = 0
    elif change == "style_missing":
        del meta["defaults"]["fill_0"]
    elif change == "color":
        style["color"] = "#FDD835"
    elif change == "transparency":
        style["transparency"] = 70
    elif change == "transparency_float":
        style["transparency"] = 90.0
    elif change == "display":
        style["display"] = 0
    elif change == "display_float":
        style["display"] = 15.0
    elif change == "visible_false":
        style["visible"] = False
    elif change == "visible_number":
        style["visible"] = 1
    elif change == "unknown_style":
        style["extra"] = True
    elif change == "dynamic_target":
        meta["plots"][3]["target"] = "fill_0"
    elif change == "dynamic_order":
        meta["plots"][3]["target"], meta["plots"][4]["target"] = "fill_2", "fill_1"
    else:
        meta["plots"].pop(3)
        meta["plots"][3]["id"] = "plot_3"
        meta["plots"][4]["id"] = "plot_4"
        meta["styles"]["plot_4"] = meta["styles"].pop("plot_5")
    with pytest.raises(ValueError):
        bind(source, meta)


@pytest.mark.parametrize(
    "replacement",
    ["color=color.yellow,transp=90", "color=color.yellow,transp=90.0", "color=color.yellow,transp=other", "color=color.yellow,display=display.none", "color=color.yellow,unknown=true", "color=#FFEB3B", "color=alias", "color=color.unknown"],
)
def test_other_unobserved_fill_forms_are_not_enabled(replacement):
    source, meta = case()
    with pytest.raises(ValueError):
        bind(source.replace("color=color.yellow)", replacement + ")", 1), meta)


def test_omitted_named_fill_does_not_enable_the_same_form_in_v5():
    source, meta = case()
    with pytest.raises(ValueError):
        bind(source.replace("//@version=4", "//@version=5").replace("study(", "indicator("), meta)

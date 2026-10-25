"""실제 d3의 두 series gradient 값과 조건부 색 세 열만 비신호로 결박한다."""

import copy

import pytest

from tests.scripts.test_pine_native_sourced_formats import bind


def case():
    source = """//@version=6
indicator("series gradient")
trend = close
upper = high
lower = low
showFill = true
trendColor = color.green
plotMid = plot(trend,"Trend Line")
plotUpper = plot(upper,"Upper Band")
plotLower = plot(lower,"Lower Band")
fill(plotUpper,plotMid,upper,trend,showFill ? color.new(trendColor,60) : na,na)
fill(plotLower,plotMid,lower,trend,showFill ? color.new(trendColor,60) : na,na)
alertcondition(close>open,title="Long")
"""
    plots = [{"id": f"plot_{i}", "type": "line"} for i in range(3)]
    for fill in range(2):
        for kind, field in [("data", "topValue"), ("data", "bottomValue"), ("colorer", "topColor")]:
            plots.append(
                {
                    "id": f"plot_{len(plots)}",
                    "type": kind,
                    "target": f"fill_{fill}",
                    "targetField": field,
                }
            )
    plots.append({"id": "plot_9", "type": "alertcondition"})
    meta = {
        "plots": plots,
        "styles": {
            f"plot_{i}": {"title": title}
            for i, title in enumerate(["Trend Line", "Upper Band", "Lower Band"])
        },
        "areas": [
            {
                "id": f"fill_{i}",
                "objAId": f"plot_{i + 1}",
                "objBId": "plot_0",
                "title": "Plots Background",
                "type": "plot_plot",
                "fillgaps": False,
                "isHidden": False,
            }
            for i in range(2)
        ],
        "defaults": {
            f"fill_{i}": {"bottomColor": "rgba(0,0,0,0)", "fillType": "gradient", "visible": True}
            for i in range(2)
        },
    }
    meta["styles"]["plot_9"] = {"title": "Long"}
    return source, meta


def test_three_gradient_columns_preserve_later_signal_coordinate():
    source, meta = case()
    assert bind(source, meta) == [(10, "long", 13)]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "order",
        "target",
        "field",
        "type",
        "palette",
        "endpoint",
        "title",
        "bottom_color",
        "visible",
        "extra_default",
    ],
)
def test_observed_gradient_roles_endpoints_and_defaults_are_exact(change):
    source, meta = case()
    if change == "missing":
        del meta["plots"][4]
    elif change == "order":
        meta["plots"][3]["targetField"], meta["plots"][4]["targetField"] = "bottomValue", "topValue"
    elif change in {"target", "field", "type", "palette"}:
        key, value = {
            "target": ("target", "fill_1"),
            "field": ("targetField", "bottomColor"),
            "type": ("type", "colorer"),
            "palette": ("palette", "palette_0"),
        }[change]
        meta["plots"][4][key] = value
    elif change == "endpoint":
        meta["areas"][0]["objBId"] = "plot_2"
    elif change == "title":
        meta["areas"][0]["title"] = "plots background"
    elif change == "bottom_color":
        meta["defaults"]["fill_0"]["bottomColor"] = "rgba(0,0,0,1)"
    elif change == "visible":
        meta["defaults"]["fill_0"]["visible"] = 1
    else:
        meta["defaults"]["fill_0"]["palette"] = "unexpected"
    with pytest.raises(ValueError):
        bind(source, meta)


@pytest.mark.parametrize(
    "old,new",
    [
        ("upper,trend,showFill", "upper,trend+1,showFill"),
        ("showFill ?", "enabled() ?"),
        (": na,na)", ": color.red,na)"),
        ("color.new(trendColor,60)", "color.new(trendColor,input.int(60))"),
        (": na,na)", ': na,na,title="Other")'),
        ("//@version=6", "//@version=5"),
    ],
)
def test_unobserved_gradient_source_shapes_remain_rejected(old, new):
    source, meta = case()
    with pytest.raises(ValueError):
        bind(source.replace(old, new), copy.deepcopy(meta))


@pytest.mark.parametrize("palettes,defaults", [({}, None), (None, {})])
def test_observed_gradient_does_not_accept_an_unobserved_palette(palettes, defaults):
    from scripts.pine_validation.native_capture import (
        _plot_bindings,
        _source_calls,
        _source_plot_variables,
    )

    source, meta = case()
    calls, _, fills = _source_calls(source)
    with pytest.raises(ValueError, match="palette"):
        _plot_bindings(
            calls,
            meta["plots"],
            meta["styles"],
            [{"function": "alertcondition", "line": 13, "column": 0, "direction": "long"}],
            fills,
            source_version=6,
            source_plot_variables=_source_plot_variables(source),
            filled_areas=meta["areas"],
            filled_area_defaults=meta["defaults"],
            palettes=palettes,
            palette_defaults=defaults,
        )

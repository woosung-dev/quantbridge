"""실제로 관측한 v4 정적 전역 fill과 기본 wick/border candle 5열만 결박한다."""

import pytest

from scripts.pine_validation.native_capture import (
    _plot_bindings,
    _source_calls,
    _source_plot_variables,
    _source_static_colors,
)

FILL_SOURCE = """//@version=4
study("readonly fill")
green90=color.new(color.green,90)
band2=plot(+1,title="A",color=color.black)
band3=plot(+3,title="B",color=color.black)
fill(band2,band3,title="Uptrend area",color=green90)
alertcondition(close>open,title="Long")
"""


def fill_case(source=FILL_SOURCE):
    calls, _, fills = _source_calls(source)
    return (
        calls,
        fills,
        {
            "plots": [
                {"id": "plot_0", "type": "line"},
                {"id": "plot_1", "type": "line"},
                {"id": "plot_2", "type": "alertcondition"},
            ],
            "styles": {
                "plot_0": {"title": "A"},
                "plot_1": {"title": "B"},
                "plot_2": {"title": "Long"},
            },
            "areas": [
                {
                    "id": "fill_0",
                    "objAId": "plot_0",
                    "objBId": "plot_1",
                    "title": "Uptrend area",
                    "type": "plot_plot",
                    "fillgaps": False,
                    "isHidden": False,
                }
            ],
            "defaults": {
                "fill_0": {
                    "color": "rgba(76,175,80,0.1)",
                    "display": 15,
                    "transparency": 90,
                    "visible": True,
                }
            },
        },
    )


def bind_fill(source, calls, fills, meta):
    return _plot_bindings(
        calls,
        meta["plots"],
        meta["styles"],
        [{"function": "alertcondition", "line": 7, "column": 0, "direction": "long"}],
        fills,
        source_plot_variables=_source_plot_variables(source),
        source_static_colors=_source_static_colors(source),
        source_version=4,
        filled_areas=meta["areas"],
        filled_area_defaults=meta["defaults"],
    )


def test_v4_readonly_named_constant_fill_preserves_signal_column():
    calls, fills, meta = fill_case()
    assert _source_static_colors(FILL_SOURCE) == {"green90": ("rgba(76,175,80,0.1)", 90)}
    assert bind_fill(FILL_SOURCE, calls, fills, meta) == [(3, "long", 7)]


@pytest.mark.parametrize(
    "mutation",
    [
        "transparency",
        "display",
        "missing_transparency",
        "extra",
        "endpoint",
        "reassignment",
        "unobserved_version",
    ],
)
def test_v4_readonly_fill_is_not_generic_constant_evaluation(mutation):
    source = FILL_SOURCE
    if mutation == "reassignment":
        source += "green90:=color.new(color.red,90)\n"
    if mutation == "unobserved_version":
        source = source.replace("version=4", "version=5")
    calls, fills, meta = fill_case(source)
    style = meta["defaults"]["fill_0"]
    if mutation == "transparency":
        style["transparency"] = 89
    elif mutation == "display":
        style["display"] = True
    elif mutation == "missing_transparency":
        del style["transparency"]
    elif mutation == "extra":
        style["width"] = 1
    elif mutation == "endpoint":
        meta["areas"][0]["objBId"] = "plot_2"
    with pytest.raises(ValueError):
        bind_fill(source, calls, fills, meta)


CANDLE_SOURCE = """//@version=4
study("candle default")
plotcandle(open,high,low,close,color=close>open?color.lime:color.fuchsia)
alertcondition(close>open,title="Long")
"""


def candle_case():
    plots = [
        {"id": f"plot_{i}", "type": kind, "target": "plotcandle_0"}
        | ({"palette": "palette_0"} if i == 4 else {})
        for i, kind in enumerate(
            ("ohlc_open", "ohlc_high", "ohlc_low", "ohlc_close", "ohlc_colorer")
        )
    ]
    plots.append({"id": "plot_5", "type": "alertcondition"})
    return {
        "plots": plots,
        "styles": {"plot_5": {"title": "Long"}},
        "ohlc": {
            "plotcandle_0": {"isHidden": False, "plottype": "ohlc_candles", "title": "PlotCandle"}
        },
        "defaults": {
            "plotcandle_0": {
                "borderColor": "#000000",
                "color": "#2196F3",
                "display": 15,
                "drawBorder": True,
                "drawWick": True,
                "visible": True,
                "wickColor": "#737375",
            }
        },
    }


def bind_candle(meta, source=CANDLE_SOURCE):
    calls, _, fills = _source_calls(source)
    return _plot_bindings(
        calls,
        meta["plots"],
        meta["styles"],
        [{"function": "alertcondition", "line": 4, "column": 0, "direction": "long"}],
        fills,
        ohlc_plots=meta["ohlc"],
        source_version=4,
        ohlc_defaults=meta["defaults"],
    )


def test_observed_five_candle_columns_bind_constant_wick_border_metadata():
    assert bind_candle(candle_case()) == [(6, "long", 4)]


@pytest.mark.parametrize(
    "mutation",
    [
        "wick",
        "border",
        "default_missing",
        "colorer_type",
        "palette",
        "target",
        "order",
        "title",
        "draw_wick",
        "explicit_wick",
    ],
)
def test_five_candle_variant_cannot_hide_missing_dynamic_columns(mutation):
    meta = candle_case()
    source = CANDLE_SOURCE
    if mutation == "wick":
        meta["defaults"]["plotcandle_0"]["wickColor"] = "#787B86"
    elif mutation == "border":
        meta["defaults"]["plotcandle_0"]["borderColor"] = "#ffffff"
    elif mutation == "default_missing":
        meta["defaults"] = {}
    elif mutation == "colorer_type":
        meta["plots"][4]["type"] = "wick_colorer"
    elif mutation == "palette":
        del meta["plots"][4]["palette"]
    elif mutation == "target":
        meta["plots"][4]["target"] = "plotcandle_1"
    elif mutation == "order":
        meta["plots"][0]["type"], meta["plots"][1]["type"] = (
            meta["plots"][1]["type"],
            meta["plots"][0]["type"],
        )
    elif mutation == "title":
        meta["ohlc"]["plotcandle_0"]["title"] = "Plot"
    elif mutation == "draw_wick":
        meta["defaults"]["plotcandle_0"]["drawWick"] = 1
    else:
        source = source.replace("color=close", "wickcolor=color.red,color=close")
    with pytest.raises(ValueError):
        bind_candle(meta, source)

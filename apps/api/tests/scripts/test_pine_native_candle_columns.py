"""실제 EVEREX/MoBars에서 관측한 candle 7열을 숨기지 않고 결박한다."""

import copy

import pytest

from scripts.pine_validation.native_capture import _plot_bindings, _source_calls

SOURCE = """//@version=5
indicator("candle control")
plotcandle(open,high,low,close,"MoBars",color.red,color.red,bordercolor=color.red)
plotchar(close,"Value",color=color.red)
alertcondition(close>open,"Long","long")
alertcondition(close<open,"Short","short")
"""


def metadata():
    types = [
        "ohlc_open",
        "ohlc_high",
        "ohlc_low",
        "ohlc_close",
        "ohlc_colorer",
        "wick_colorer",
        "border_colorer",
    ]
    plots = [
        {"id": f"plot_{i}", "type": kind, "target": "plotcandle_0"}
        | ({"palette": f"palette_{i - 4}"} if i >= 4 else {})
        for i, kind in enumerate(types)
    ]
    plots += [
        {"id": "plot_7", "type": "chars"},
        {"id": "plot_8", "type": "colorer", "target": "plot_7", "palette": "palette_3"},
        {"id": "plot_9", "type": "alertcondition"},
        {"id": "plot_10", "type": "alertcondition"},
    ]
    styles = {
        "plot_7": {"title": "Value"},
        "plot_9": {"title": "Long", "text": "long"},
        "plot_10": {"title": "Short", "text": "short"},
    }
    candles = {"plotcandle_0": {"title": "MoBars", "plottype": "ohlc_candles"}}
    return plots, styles, candles


def bind(plots, styles, candles):
    calls, _, fills = _source_calls(SOURCE)
    reviewed = [
        {"function": "alertcondition", "line": 5, "column": 0, "direction": "long"},
        {"function": "alertcondition", "line": 6, "column": 0, "direction": "short"},
    ]
    return _plot_bindings(calls, plots, styles, reviewed, fills, ohlc_plots=candles)


def test_exact_candle_group_preserves_subsequent_native_signal_columns():
    assert bind(*metadata()) == [(10, "long", 5), (11, "short", 6)]


@pytest.mark.parametrize("change", ["order", "target", "price_palette", "title", "type", "extra"])
def test_candle_column_or_style_tampering_cannot_move_signal_bindings(change):
    plots, styles, candles = copy.deepcopy(metadata())
    if change == "order":
        plots[1]["type"], plots[2]["type"] = plots[2]["type"], plots[1]["type"]
    elif change == "target":
        plots[4]["target"] = "plotcandle_1"
    elif change == "price_palette":
        plots[0]["palette"] = "palette_0"
    elif change == "title":
        candles["plotcandle_0"]["title"] = "Other"
    elif change == "type":
        candles["plotcandle_0"]["plottype"] = "ohlc_bars"
    else:
        candles["plotcandle_1"] = candles["plotcandle_0"]
    with pytest.raises(ValueError):
        bind(plots, styles, candles)

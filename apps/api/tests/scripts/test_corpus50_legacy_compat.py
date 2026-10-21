"""수집한 Donchian, Hull, QQE 원문의 별칭·표시 상수 회귀."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical


def _candles() -> pd.DataFrame:
    closes = [10.0, 12.0, 11.0, 15.0, 13.0, 17.0]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value + 1 for value in closes],
            "low": [value - 1 for value in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


@pytest.mark.parametrize(
    "legacy,namespaced,third_bar",
    [
        ("avg(high, low)", "math.avg(high, low)", 11.0),
        ("wma(close, 3)", "ta.wma(close, 3)", 67 / 6),
        ("round(sqrt(9))", "math.round(math.sqrt(9))", 3),
    ],
)
def test_collected_v4_calls_reuse_existing_namespace_implementations(
    legacy: str, namespaced: str, third_bar: float
) -> None:
    source = f'//@version=4\nstudy("source calls")\na = {legacy}\nb = {namespaced}\n'
    coverage = analyze_coverage(source)
    assert coverage.is_runnable, coverage.all_unsupported
    result = run_historical(source, _candles())
    assert result.var_series["a"][2] == pytest.approx(third_bar)
    for actual, expected in zip(result.var_series["a"], result.var_series["b"], strict=True):
        assert actual == expected or (math.isnan(actual) and math.isnan(expected))


def test_qqe_column_style_is_display_only_constant() -> None:
    source = '//@version=6\nindicator("QQE columns")\nplot(close, style=plot.style_columns)\n'
    coverage = analyze_coverage(source)
    assert coverage.is_runnable, coverage.all_unsupported
    assert run_historical(source, _candles()).bars_processed == 6


def test_unknown_plot_style_stays_unsupported() -> None:
    source = '//@version=6\nindicator("unknown")\nplot(close, style=plot.style_unknown)\n'
    assert analyze_coverage(source).unsupported_attributes == ("plot.style_unknown",)


@pytest.mark.parametrize("style", ["solid", "dashed", "dotted"])
def test_rsi_signals_horizontal_line_styles_do_not_block_execution(style: str) -> None:
    source = (
        '//@version=5\nindicator("RSI signal levels")\n'
        f'hline(70, title="Overbought", linestyle=hline.style_{style})\n'
        'plotshape(close > open, title="Buy")\n'
    )
    assert analyze_coverage(source).is_runnable
    assert run_historical(source, _candles()).bars_processed == 6

"""Signal Extractor — C-text / C-ast 두 방식 TDD."""

from __future__ import annotations

from src.strategy.pine_v2.signal_extractor import SignalExtractor

# ─── Fixtures ─────────────────────────────────────────────────────────────────

_SIMPLE_PLOTSHAPE = """\
//@version=5
indicator("Simple Test", overlay=true)
len = input.int(20, "Length")
arr = array.new_float(0)
box.new(bar_index, high, bar_index + 5, low, color.red)
bull = ta.crossover(close, ta.sma(close, len))
bear = ta.crossunder(close, ta.sma(close, len))
plotshape(bull, "Buy", shape.triangleup, location.belowbar, color.green)
plotshape(bear, "Sell", shape.triangledown, location.abovebar, color.red)
"""

_UDF_PLOTSHAPE = """\
//@version=5
indicator("UDF Test", overlay=true)
factor = input.float(3.0, "Factor")
atrLen = input.int(14, "ATR Len")
supertrend(src, f, aLen) =>
    atr = ta.atr(aLen)
    up = src - f * atr
    [up, up]
[st, _] = supertrend(close, factor, atrLen)
bull = ta.crossover(close, st)
label.new(bull ? bar_index : na, high, "B")
array.new_box(10)
"""

_STRATEGY_ENTRY = """\
//@version=5
strategy("Entry Test", overlay=true)
fast = input.int(9)
slow = input.int(21)
fast_ma = ta.sma(close, fast)
slow_ma = ta.sma(close, slow)
buy_sig  = ta.crossover(fast_ma, slow_ma)
sell_sig = ta.crossunder(fast_ma, slow_ma)
strategy.entry("Long", strategy.long, when=buy_sig)
strategy.entry("Short", strategy.short, when=sell_sig)
"""


# ─── C-text Tests ─────────────────────────────────────────────────────────────


class TestCText:
    def test_finds_plotshape_signal_vars(self) -> None:
        r = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="text")
        assert "bull" in r.signal_vars
        assert "bear" in r.signal_vars

    def test_removes_drawing_api(self) -> None:
        r = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="text")
        assert "array.new_float" not in r.sliced_code
        assert "box.new" not in r.sliced_code

    def test_preserves_inputs(self) -> None:
        r = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="text")
        assert "input.int" in r.sliced_code

    def test_adds_strategy_entry(self) -> None:
        r = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="text")
        assert "strategy.entry" in r.sliced_code

    def test_simple_is_runnable(self) -> None:
        r = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="text")
        assert r.is_runnable

    def test_tracks_udf_dependency(self) -> None:
        r = SignalExtractor().extract(_UDF_PLOTSHAPE, mode="text")
        assert "supertrend" in r.sliced_code
        assert "ta.atr" in r.sliced_code

    def test_token_reduction_is_positive(self) -> None:
        r = SignalExtractor().extract(_UDF_PLOTSHAPE, mode="text")
        assert r.token_reduction_pct > 0

    def test_strategy_entry_source_is_runnable(self) -> None:
        r = SignalExtractor().extract(_STRATEGY_ENTRY, mode="text")
        assert r.is_runnable


# ─── C-ast Tests ──────────────────────────────────────────────────────────────


class TestCAst:
    def test_finds_same_vars_as_ctext(self) -> None:
        r_text = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="text")
        r_ast = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="ast")
        assert set(r_text.signal_vars) == set(r_ast.signal_vars)

    def test_simple_is_runnable(self) -> None:
        r = SignalExtractor().extract(_SIMPLE_PLOTSHAPE, mode="ast")
        assert r.is_runnable

    def test_udf_dependency_tracked(self) -> None:
        r = SignalExtractor().extract(_UDF_PLOTSHAPE, mode="ast")
        assert "supertrend" in r.sliced_code

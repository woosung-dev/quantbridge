"""부분 청산 수량을 무시한 전량 청산이 정상 성과로 나가지 않게 한다."""

import pandas as pd
import pytest

from src.backtest.engine import BacktestConfig, run_backtest
from src.strategy.pine_v2.coverage import analyze_coverage


def _candles():
    return pd.DataFrame(
        {
            "open": [100, 100, 100],
            "high": [101, 111, 101],
            "low": [99, 99, 89],
            "close": [100, 110, 90],
            "volume": [10] * 3,
        },
        index=pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC"),
    )


@pytest.mark.parametrize(
    "arguments",
    [
        '"half", "L", limit=110, qty_percent=50',
        '"half", "L", limit=110, qty=5',
        'id="half", from_entry="L", limit=110,\n         qty_percent=math.max(20, 50)',
    ],
)
def test_named_partial_quantity_preserves_remaining_stop(arguments):
    source = f"""//@version=5
strategy("Partial quantity", default_qty_type=strategy.fixed, default_qty_value=10)
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
    strategy.exit({arguments})
    strategy.exit("remaining", "L", stop=90)
"""
    assert analyze_coverage(source).is_runnable
    outcome = run_backtest(source, _candles(), BacktestConfig(fees=0, slippage=0, maker_fee=0))
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    trades = outcome.result.trades
    assert len(trades) == 2
    assert [trade.size for trade in trades] == [5, 5]
    assert [trade.exit_price for trade in trades] == [110, 90]
    assert all(trade.status == "closed" for trade in trades)


@pytest.mark.parametrize(
    ("arguments", "unsupported"),
    [
        ('"half", "L", 5, limit=110', "qty"),
        ('"half", "L", na, 50, limit=110', "qty_percent"),
    ],
)
def test_positional_quantity_is_rejected_before_submission_and_at_runtime(arguments, unsupported):
    source = f"""//@version=5
strategy("Partial guard", default_qty_type=strategy.fixed, default_qty_value=10)
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
strategy.exit({arguments})
"""
    coverage = analyze_coverage(source)
    assert not coverage.is_runnable
    assert f"strategy.exit.{unsupported}" in coverage.all_unsupported
    assert any(item["line"] == 5 for item in coverage.unsupported_calls)
    result = run_backtest(source, _candles())
    assert result.status == "error" and result.result is None
    assert "strategy.exit unsupported arguments" in result.error


def test_quantity_in_comments_or_other_calls_does_not_block_full_exit():
    source = """//@version=5
strategy("Exit qty_percent=50", default_qty_type=strategy.fixed, default_qty_value=10)
strategy.entry("L", strategy.long, qty=10)
// strategy.exit("half", "L", qty_percent=50)
strategy.exit("full", "L", limit=110, stop=95)
"""
    assert analyze_coverage(source).is_runnable

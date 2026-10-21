"""부분 청산 수량을 무시한 전량 청산이 정상 성과로 나가지 않게 한다."""

import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.strategy.pine_v2.coverage import analyze_coverage


@pytest.mark.parametrize(
    ("arguments", "unsupported"),
    [
        ('"half", "L", limit=110, qty_percent=50', "qty_percent"),
        ('"half", "L", limit=110, qty=5', "qty"),
        ('"half", "L", 5, limit=110', "qty"),
        ('"half", "L", na, 50, limit=110', "qty_percent"),
        ('id="half", from_entry="L", limit=110,\n     qty_percent=math.max(20, 50)', "qty_percent"),
    ],
)
def test_partial_quantity_is_rejected_before_submission_and_at_runtime(arguments, unsupported):
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
    prices = [100, 100, 110]
    frame = pd.DataFrame(
        {
            "open": prices,
            "high": [101, 111, 111],
            "low": [99, 99, 109],
            "close": prices,
            "volume": [10] * 3,
        },
        index=pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC"),
    )
    result = run_backtest(source, frame)
    assert result.status == "error" and result.result is None
    assert "부분 청산" in result.error


def test_quantity_in_comments_or_other_calls_does_not_block_full_exit():
    source = """//@version=5
strategy("Exit qty_percent=50", default_qty_type=strategy.fixed, default_qty_value=10)
strategy.entry("L", strategy.long, qty=10)
// strategy.exit("half", "L", qty_percent=50)
strategy.exit("full", "L", limit=110, stop=95)
"""
    assert analyze_coverage(source).is_runnable

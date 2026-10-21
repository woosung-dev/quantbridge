"""Pine 내부 broker 없이 공통 원장의 포지션으로 의도를 계산한다."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.code_runtime.models import CodeRuntimeError
from tests.strategy.code_runtime.test_backtest import cfg, frame


def test_pine_entry_close_and_position_feedback_follow_external_ledger() -> None:
    source = """//@version=5
strategy("external ledger")
if bar_index == 1
    strategy.entry("L", strategy.long)
if strategy.position_size > 0 and bar_index == 2
    strategy.close("L")
if strategy.position_size == 0 and bar_index == 3
    strategy.entry("S", strategy.short)
"""
    trace: list[dict[str, Any]] = []
    result = run_code_backtest(
        source,
        "pine",
        frame([(100, 110, 90, 100)] * 5),
        cfg(),
        trace=trace,
    )
    assert [
        (trade.direction, trade.entry_bar_index, trade.exit_bar_index) for trade in result.trades
    ] == [
        ("long", 2, 3),
        ("short", 4, None),
    ]
    assert result.trades[0].pnl == Decimal(0)
    assert [event["action"] for event in trace if event["type"] == "intent"] == [
        "hold",
        "long",
        "close",
        "short",
        "hold",
    ]


def test_pine_partial_exit_feedback_is_visible_to_following_signal() -> None:
    source = """//@version=5
strategy("remaining size")
if bar_index == 1
    strategy.entry("L", strategy.long)
if strategy.position_size == 5
    strategy.close("L")
"""
    result = run_code_backtest(
        source,
        "pine",
        frame(
            [
                (100, 110, 90, 100),
                (100, 110, 91, 100),
                (100, 117, 100, 117),
                (117, 119, 115, 118),
            ]
        ),
        cfg(),
    )
    assert result.trades[0].exit_bar_index == 3
    assert result.trades[0].pnl == Decimal("167.5")


@pytest.mark.parametrize(
    "order",
    [
        'strategy.exit("X", "L", stop=90)',
        'strategy.entry("L", strategy.long, stop=105)',
        'strategy.entry("L", strategy.long, qty=2)',
        "strategy.cancel_all()",
    ],
)
def test_pine_rejects_unrepresentable_order_semantics(order: str) -> None:
    with pytest.raises(CodeRuntimeError):
        run_code_backtest(
            f'//@version=5\nstrategy("unsupported intent")\n{order}\n',
            "pine",
            frame([(100, 110, 90, 100)] * 3),
            cfg(),
        )


def test_pine_opposite_entry_wins_over_close_for_atomic_reversal_intent() -> None:
    source = """//@version=5
strategy("reverse")
if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 2
    strategy.close("L")
    strategy.entry("S", strategy.short)
"""
    result = run_code_backtest(source, "pine", frame([(100, 110, 90, 100)] * 4), cfg())
    assert [trade.direction for trade in result.trades] == ["long", "short"]
    assert result.trades[0].exit_bar_index == result.trades[1].entry_bar_index == 3

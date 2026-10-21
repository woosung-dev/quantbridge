"""언어와 무관한 실제 fill R·부분 청산·반전·펀딩 계약."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.code_runtime.models import CodeRuntimeError

D = Decimal


class Tape:
    def __init__(self, signals: dict[int, dict[str, str]]) -> None:
        self.signals = signals
        self.messages: list[dict[str, Any]] = []
        self.closed = False

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        self.messages.append(deepcopy(message))
        if message["type"] == "init":
            return {"ready": 1}
        return {"intent": self.signals.get(message["bar"]["index"], {"action": "hold"})}

    def close(self) -> None:
        self.closed = True


def frame(bars: list[tuple[int, int, int, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                **{
                    key: D(value)
                    for key, value in zip(("open", "high", "low", "close"), bar, strict=True)
                },
                "volume": D(1),
            }
            for bar in bars
        ],
        index=pd.date_range("2026-01-01", periods=len(bars), freq="1h", tz="UTC"),
    )


def cfg(**changes: Any) -> BacktestConfig:
    return replace(
        BacktestConfig(
            freq="1h",
            fees=0,
            slippage=0,
            maker_fee=0,
            default_qty_type="strategy.fixed",
            default_qty_value=10,
        ),
        **changes,
    )


def run(bars: list[tuple[int, int, int, int]], signals: dict[int, dict[str, str]], **kwargs: Any):
    tape = Tape(signals)
    trace: list[dict[str, Any]] = []
    result = run_code_backtest(
        "unexecuted test source",
        "python",
        frame(bars),
        kwargs.pop("config", cfg()),
        transport_factory=lambda: tape,
        trace=trace,
        **kwargs,
    )
    return result, tape, trace


def test_actual_gap_fill_r_and_first_fill_bar_stop() -> None:
    result, tape, trace = run(
        [(100, 110, 90, 100), (100, 110, 91, 100), (110, 112, 87, 100)],
        {1: {"action": "long"}},
    )
    fills = [event for event in trace if event["type"] == "fill"]
    assert fills[0]["price"] == "110"
    assert fills[0]["plan"]["risk"] == "22.00"
    assert fills[0]["plan"]["stop_loss"] == "88.00"
    assert fills[1]["kind"] == "stop_loss" and fills[1]["price"] == "88.00"
    assert result.trades[0].pnl == D(-220)
    assert result.trades[0].entry_bar_index == result.trades[0].exit_bar_index == 2
    assert result.config_used.fill_timing == "next_bar_open"
    assert result.trades[0].entry_phase == "bar_open"
    assert result.trades[0].exit_phase == "intrabar_unknown"
    assert tape.closed


def test_partial_once_trailing_and_position_feedback_uses_remaining_quantity() -> None:
    result, tape, trace = run(
        [
            (100, 110, 90, 100),
            (100, 110, 91, 100),
            (100, 117, 100, 117),
            (117, 125, 117, 124),
            (124, 124, 102, 103),
        ],
        {1: {"action": "long"}, 2: {"action": "long"}},
    )
    fills = [event for event in trace if event["type"] == "fill"]
    assert [event["kind"] for event in fills] == ["entry", "partial_tp", "trailing_stop"]
    assert fills[1]["quantity"] == "5.0" and D(fills[1]["price"]) == D("116.5")
    assert fills[2]["quantity"] == "5.0" and D(fills[2]["price"]) == D(103)
    assert result.metrics.num_trades == 1
    assert result.trades[0].pnl == D("97.5")
    assert tape.messages[3]["position"]["size"] == "5.0"


def test_source_invalidation_close_is_honored_on_next_open() -> None:
    result, _, trace = run(
        [(100, 110, 90, 100), (100, 110, 91, 100), (100, 105, 95, 101), (102, 105, 98, 100)],
        {1: {"action": "long"}, 2: {"action": "close"}},
    )
    assert result.trades[0].exit_price == D(102)
    assert result.trades[0].exit_bar_index == 3
    assert [event["kind"] for event in trace if event["type"] == "fill"] == ["entry", "close"]


def test_reversal_uses_fresh_two_bar_plan_and_costs() -> None:
    result, _, trace = run(
        [(100, 110, 90, 100), (100, 110, 91, 100), (100, 108, 95, 101), (102, 106, 98, 100)],
        {1: {"action": "long"}, 2: {"action": "short"}},
        config=cfg(fees=0.001, slippage=0.002),
    )
    fills = [event for event in trace if event["type"] == "fill"]
    assert [event["kind"] for event in fills] == ["entry", "close", "entry"]
    assert fills[-1]["direction"] == "short"
    assert fills[-1]["plan"]["reference_extreme"] == "110"
    assert D(fills[-1]["plan"]["risk"]) == D("8.8")
    assert result.trades[0].fees == D("6.06")


def test_funding_before_next_open_close_uses_remaining_quantity() -> None:
    bars = [(100, 110, 90, 100), (100, 110, 91, 100), (100, 117, 100, 117), (117, 119, 115, 118)]
    rates = pd.Series([D("0.001")], index=frame(bars).index[3:])
    result, _, trace = run(
        bars,
        {1: {"action": "long"}, 2: {"action": "close"}},
        config=cfg(include_funding=True),
        funding_rates=rates,
    )
    assert result.metrics.total_funding == D("0.585")
    assert next(event for event in trace if event["type"] == "funding")["amount"] == "0.5850"
    assert result.metrics.net_profit_abs == result.metrics.total_return * D(10000)


def test_warmup_updates_code_without_trading_or_leaking_future_bars() -> None:
    result, tape, _ = run(
        [(100, 110, 90, 100), (100, 110, 91, 100), (100, 105, 95, 100), (100, 105, 95, 100)],
        {0: {"action": "long"}, 1: {"action": "long"}, 2: {"action": "long"}},
        warmup_bars=2,
    )
    assert result.trades[0].entry_bar_index == 1
    assert len(result.equity_curve) == 2
    assert len(tape.messages) == 5
    assert all("history" not in message for message in tape.messages)


def test_intent_order_fields_fail_closed_and_transport_always_closes() -> None:
    tape = Tape({1: {"action": "long", "stop_loss": "1"}})
    with pytest.raises(CodeRuntimeError, match="action 하나"):
        run_code_backtest(
            "source",
            "typescript",
            frame([(100, 110, 90, 100)] * 3),
            cfg(),
            transport_factory=lambda: tape,
        )
    assert tape.closed


def test_last_bar_signal_is_unfilled() -> None:
    result, _, _ = run([(100, 110, 90, 100)] * 3, {2: {"action": "short"}})
    assert result.trades == []

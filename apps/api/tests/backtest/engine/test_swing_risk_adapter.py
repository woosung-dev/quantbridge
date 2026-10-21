"""분봉 시계·부분 실현·펀딩·격리 신호 경계를 합성 가격으로 검증한다."""

from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pandas as pd
import pytest

from src.backtest.engine.swing_risk_adapter import run_swing_risk_backtest
from src.backtest.engine.types import BacktestConfig
from src.strategy.python_runtime.protocol import PythonRuntimeError

D = Decimal
SOURCE = "def on_bar(ctx,state): return {'action':'hold'}"


class Tape:
    image_id = "sha256:test"

    def __init__(self, signals: dict[int, dict[str, str]]) -> None:
        self.signals = signals
        self.messages: list[dict[str, Any]] = []
        self.closed = False

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        self.messages.append(copy.deepcopy(message))
        if message["type"] == "init":
            return {"ready": 1}
        return {"intent": self.signals.get(message["bar"]["index"], {"action": "hold"})}

    def close(self) -> None:
        self.closed = True


def data(
    hours: int = 4, changes: dict[int, tuple[str, str, str, str]] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.DataFrame(
        {"open": D("100"), "high": D("101"), "low": D("99"), "close": D("100"), "volume": D("1")},
        index=pd.date_range("2026-01-01", periods=hours * 60, freq="1min", tz="UTC"),
    )
    frame.iloc[0, frame.columns.get_loc("low")] = D("90")
    frame.iloc[60, frame.columns.get_loc("low")] = D("95")
    for minute, values in (changes or {}).items():
        for name, value in zip(("open", "high", "low", "close"), values, strict=True):
            frame.iloc[minute, frame.columns.get_loc(name)] = D(value)
    parent = frame.resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return parent, frame


def cfg(**changes: Any) -> BacktestConfig:
    return replace(
        BacktestConfig(
            freq="1h",
            fill_timing="next_bar_open",
            fees=0,
            slippage=0,
            maker_fee=0,
            default_qty_type="strategy.fixed",
            default_qty_value=10,
        ),
        **changes,
    )


def run(
    signals: dict[int, dict[str, str]],
    *,
    changes: dict[int, tuple[str, str, str, str]] | None = None,
    config: BacktestConfig | None = None,
    funding: pd.Series | None = None,
    warmup: int = 0,
) -> tuple[dict[str, Any], Tape]:
    parent, minute = data(changes=changes)
    tape = Tape(signals)
    result = run_swing_risk_backtest(
        SOURCE,
        parent,
        minute.iloc[warmup * 60 :],
        config or cfg(),
        funding,
        warmup_bars=warmup,
        transport_factory=lambda: tape,
    )
    return result, tape


def test_next_open_uses_signal_and_previous_closed_bars_and_one_position_episode() -> None:
    result, tape = run(
        {1: {"action": "long"}},
        changes={
            120: ("100", "117", "100", "117"),
            121: ("117", "125", "117", "124"),
            122: ("124", "124", "102", "103"),
        },
    )
    entry, partial, trailing = result["fill_events"]
    assert entry["timestamp"] == "2026-01-01T02:00:00+00:00"
    assert entry["plan"]["reference_extreme"] == "90"
    assert entry["plan"]["stop_loss"] == "89.00"
    assert entry["plan"]["risk"] == "11.00"
    assert partial["kind"] == "partial_tp" and partial["quantity"] == "5.0"
    assert partial["price"] == "116.500"
    assert trailing["kind"] == "trailing_stop" and trailing["price"] == "103.00"
    assert result["metrics"]["num_trades"] == 1
    assert D(result["metrics"]["net_profit_abs"]) == D("97.5")
    assert D(result["metrics"]["total_return"]) * D("10000") == D("97.5")
    assert len(result["equity_curve"]) == 4
    assert len([m for m in tape.messages if m["type"] == "bar"]) == 4
    assert tape.closed


def test_same_direction_keeps_partial_and_stop_state_and_source_exits_are_replaced() -> None:
    result, _ = run(
        {
            1: {"action": "long"},
            2: {"action": "long", "stop_loss": "99", "take_profit": "101"},
            3: {"action": "close"},
        },
        changes={120: ("100", "117", "100", "117")},
    )
    assert result["counters"]["entry"] == 1
    assert result["counters"]["partial_tp"] == 1
    assert result["counters"]["same_direction_ignored"] == 1
    assert result["counters"]["source_exit_ignored"] == 2
    assert result["trades"][0]["status"] == "open"
    assert D(result["metrics"]["open_pnl"]) == D("82.5")


def test_reverse_closes_only_remaining_quantity_and_new_generation_has_its_own_plan() -> None:
    result, _ = run(
        {1: {"action": "long"}, 2: {"action": "short"}}, changes={120: ("100", "117", "100", "117")}
    )
    fills = result["fill_events"]
    assert [f["kind"] for f in fills] == ["entry", "partial_tp", "close", "entry"]
    assert fills[2]["quantity"] == "5.0"
    assert fills[3]["generation"] == 2
    assert fills[3]["direction"] == "short"
    assert result["metrics"]["num_trades"] == 1
    assert result["metrics"]["total_open_trades"] == 1


def test_bar_close_does_not_replay_already_observed_parent_high_for_new_position() -> None:
    result, _ = run(
        {1: {"action": "long"}},
        config=cfg(fill_timing="bar_close"),
        changes={60: ("100", "140", "95", "100")},
    )
    assert [event["kind"] for event in result["fill_events"]] == ["entry"]
    assert result["fill_events"][0]["phase"] == "parent_close"
    assert result["trades"][0]["status"] == "open"


def test_funding_uses_remaining_quantity_and_precedes_new_open_entry() -> None:
    _, minute = data()
    rates = pd.Series([D("0.01"), D("0.01")], index=minute.index[[120, 121]], dtype=object)
    result, _ = run(
        {1: {"action": "long"}},
        config=cfg(include_funding=True),
        funding=rates,
        changes={120: ("100", "117", "100", "117"), 121: ("117", "118", "116", "117")},
    )
    assert D(result["metrics"]["total_funding"]) == D("5.85")
    assert D(result["metrics"]["open_pnl"]) == D("76.65")
    assert result["assumptions"]["funding_order"] == "minute_open_before_queued_market_orders"
    assert result["metrics"]["funding_data_incomplete"] is None


def test_entry_cost_is_once_and_partial_and_final_exit_costs_are_each_charged() -> None:
    result, _ = run(
        {1: {"action": "long"}},
        config=cfg(fees=0.001, slippage=0.002, maker_fee=0.0005),
        changes={
            120: ("100", "117", "100", "117"),
            121: ("117", "125", "117", "124"),
            122: ("124", "124", "102", "103"),
        },
    )
    assert D(result["metrics"]["total_fees"]) == D("1.80625")
    assert D(result["metrics"]["total_slippage"]) == D("3.03000")
    assert D(result["metrics"]["net_profit_abs"]) == D("97.5") - D("4.83625")


def test_partial_and_final_fill_in_one_minute_keep_one_episode_and_cash_reconciled() -> None:
    result, _ = run({1: {"action": "long"}}, changes={120: ("100", "130", "100", "110")})
    assert [event["kind"] for event in result["fill_events"]] == [
        "entry",
        "partial_tp",
        "trailing_stop",
    ]
    assert result["metrics"]["num_trades"] == 1
    assert D(result["metrics"]["net_profit_abs"]) == D("122.5")
    assert D(result["equity_curve"][-1]["value"]) == D("10122.5")
    assert len(result["metrics"]["drawdown_curve"]) == 4
    assert len(result["metrics"]["buy_and_hold_curve"]) == 4


def test_short_partial_and_trailing_are_direction_symmetric() -> None:
    result, _ = run(
        {1: {"action": "short"}},
        changes={
            120: ("100", "100", "98", "98"),
            121: ("98", "98", "97", "97.5"),
            122: ("97.5", "99.5", "97.5", "99.2"),
        },
    )
    assert [event["kind"] for event in result["fill_events"]] == [
        "entry",
        "partial_tp",
        "trailing_stop",
    ]
    assert result["metrics"]["num_trades"] == 1
    assert D(result["metrics"]["net_profit_abs"]) == D("12.25")


def test_warmup_is_not_traded_and_future_bars_are_not_sent_to_source() -> None:
    result, tape = run(
        {0: {"action": "short"}, 1: {"action": "long"}, 3: {"action": "short"}}, warmup=1
    )
    assert result["counters"]["entry"] == 1
    assert result["signals"][-1]["disposition"] == "queued_unfilled"
    assert tape.messages[1]["position"]["direction"] == "flat"
    assert set(tape.messages[2]) == {"type", "bar", "position"}
    assert len(result["equity_curve"]) == 3


@pytest.mark.parametrize("broken", ["gap", "mismatch", "nonfinite"])
def test_invalid_execution_data_is_rejected_before_source_execution(broken: str) -> None:
    parent, minute = data()
    if broken == "gap":
        minute = minute.drop(minute.index[123])
    elif broken == "mismatch":
        parent.iloc[1, parent.columns.get_loc("high")] = D("1000")
    else:
        minute.iloc[123, minute.columns.get_loc("close")] = D("NaN")

    def forbidden() -> Any:
        raise AssertionError("잘못된 입력에서 실행기를 시작했습니다")

    with pytest.raises(PythonRuntimeError):
        run_swing_risk_backtest(SOURCE, parent, minute, cfg(), transport_factory=forbidden)


def test_protocol_error_closes_transport_and_returns_no_partial_result() -> None:
    parent, minute = data()
    tape = Tape({2: {"action": "buy"}})
    with pytest.raises(PythonRuntimeError):
        run_swing_risk_backtest(SOURCE, parent, minute, cfg(), transport_factory=lambda: tape)
    assert tape.closed


def test_source_baseline_honors_original_close_without_swing_or_two_bar_gate() -> None:
    parent, minute = data(changes={180: ("110", "111", "109", "110")})
    tape = Tape({0: {"action": "long"}, 2: {"action": "close"}})
    result = run_swing_risk_backtest(
        SOURCE, parent, minute, cfg(), transport_factory=lambda: tape, exit_policy="source"
    )
    assert [event["kind"] for event in result["fill_events"]] == ["entry", "close"]
    assert result["fill_events"][0]["timestamp"] == "2026-01-01T01:00:00+00:00"
    assert result["fill_events"][0]["plan"] is None
    assert result["fill_events"][1]["timestamp"] == "2026-01-01T03:00:00+00:00"
    assert result["metrics"]["num_trades"] == 1
    assert D(result["metrics"]["net_profit_abs"]) == D("100")
    assert result["exit_policy"] == "source"
    assert result["risk_policy"] is None
    assert tape.messages[2]["position"]["direction"] == "long"


def test_source_baseline_and_swing_use_same_net_sizing_and_funding_model() -> None:
    parent, minute = data()
    rates = pd.Series([D("0.01")], index=minute.index[[121]], dtype=object)
    outputs = []
    for policy in ("source", "swing"):
        outputs.append(
            run_swing_risk_backtest(
                SOURCE,
                parent,
                minute,
                cfg(
                    include_funding=True,
                    fees=0.001,
                    default_qty_type="strategy.percent_of_equity",
                    default_qty_value=100,
                ),
                rates,
                transport_factory=lambda: Tape({1: {"action": "long"}}),
                exit_policy=policy,
            )
        )
    source, swing = outputs
    assert source["metrics"] == swing["metrics"]
    assert source["equity_curve"] == swing["equity_curve"]
    assert source["metrics"]["total_funding"] == "100.00"
    assert source["fill_events"][0]["quantity"] == swing["fill_events"][0]["quantity"]


def test_source_baseline_rejects_bracket_output_without_silent_success() -> None:
    parent, minute = data()
    tape = Tape({1: {"action": "long", "stop_loss": "90"}})
    with pytest.raises(PythonRuntimeError, match="SL/TP"):
        run_swing_risk_backtest(
            SOURCE, parent, minute, cfg(), transport_factory=lambda: tape, exit_policy="source"
        )
    assert tape.closed


@pytest.mark.parametrize(
    "options,field",
    [
        ({"trading_sessions": ("asia",)}, "trading_sessions"),
        ({"input_overrides": {"period": 12}}, "input_overrides"),
        ({"input_overrides": {}}, "input_overrides"),
        ({"live_position_size_pct": 50}, "live_position_size_pct"),
        ({"live_position_size_pct": float("nan")}, "live_position_size_pct"),
    ],
)
def test_unsupported_config_is_rejected_before_transport(
    options: dict[str, Any], field: str
) -> None:
    parent, minute = data()

    def forbidden() -> Any:
        raise AssertionError("미지원 옵션에서 실행기를 시작했습니다")

    with pytest.raises(PythonRuntimeError, match=field):
        run_swing_risk_backtest(SOURCE, parent, minute, cfg(**options), transport_factory=forbidden)

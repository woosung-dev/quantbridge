"""명시적 연구 정책의 재진입·공유 신호·기간 경계를 실제 원장으로 검사한다."""

from copy import deepcopy
from decimal import Decimal
from typing import Any

import pandas as pd
import pytest

from src.backtest.engine.swing_risk_adapter import _Ledger
from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.python_runtime.swing_risk import RiskEvent
from src.strategy.research_contract import ResearchExecution
from tests.strategy.code_runtime.test_backtest import Tape, cfg, frame

D = Decimal


def policy(exit_policy: str = "swing_two_bar_v1", **changes: Any) -> ResearchExecution:
    return ResearchExecution.model_validate(
        {
            "contract_version": 1,
            "exit_policy": exit_policy,
            "reentry_policy": "close_then_reenter_v1",
            "signal_mode": "shared_events",
            "signal_mapping_hash": "a" * 64,
            **changes,
        }
    )


def execute(bars, signals, *, research=None, **kwargs):
    transport = Tape(signals)
    trace: list[dict[str, Any]] = []
    result = run_code_backtest(
        "reviewed source",
        "python",
        frame(bars),
        kwargs.pop("config", cfg()),
        research_policy=research or policy(),
        transport_factory=lambda: transport,
        trace=trace,
        **kwargs,
    )
    return result, transport, trace


def fills(trace):
    return [row for row in trace if row["type"] == "fill"]


@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("opposite", [False, True])
@pytest.mark.parametrize("stage", ["initial", "partial", "trailing"])
def test_new_event_closes_remaining_and_creates_fresh_episode(direction, opposite, stage):
    bars = [(100, 110, 90, 100), (100, 110, 91, 100)]
    if stage == "initial":
        bars.extend([(100, 105, 95, 100), (100, 105, 95, 100)])
    else:
        bars.append((100, 117, 100, 117))
        if stage == "trailing":
            bars.append((117, 125, 115, 124))
        bars.append((112, 113, 111, 112))
    if direction == "short":
        bars = [(200 - o, 200 - low, 200 - h, 200 - c) for o, h, low, c in bars]
    next_direction = ("short" if direction == "long" else "long") if opposite else direction
    signal_index = len(bars) - 2
    result, _, trace = execute(
        bars, {1: {"action": direction}, signal_index: {"action": next_direction}}
    )
    events = fills(trace)
    closing = next(row for row in events if row["kind"] == "close")
    assert D(closing["quantity"]) == (D(10) if stage == "initial" else D(5))
    assert closing["exit_reason"] == (
        "opposite_direction_reversal" if opposite else "same_direction_reentry"
    )
    assert len(result.trades) == 2
    assert result.trades[0].status == "closed"
    assert result.trades[1].status == "open"
    entries = [row for row in events if row["kind"] == "entry"]
    assert entries[1]["episode_id"] == 2
    assert D(entries[1]["quantity"]) == D(10)
    assert entries[1]["plan"]["generation"] == 2
    assert entries[1]["plan"]["initial_qty"] == "10"
    assert closing["signal_event_id"] == entries[1]["signal_event_id"]
    assert entries[0]["signal_event_id"] != entries[1]["signal_event_id"]
    assert (
        next(row for row in reversed(trace) if row["type"] == "intent")["risk_state"]["tp_filled"]
        is False
    )


def test_signal_only_has_no_swing_history_gate_or_protection_and_keeps_open_mark():
    result, _, trace = execute(
        [(100, 101, 99, 100), (100, 110, 1, 105)],
        {0: {"action": "long"}},
        research=policy("signal_only_v1"),
    )
    assert [row["kind"] for row in fills(trace)] == ["entry"]
    assert fills(trace)[0]["plan"] is None
    assert result.trades[0].status == "open"
    assert result.metrics.open_pnl == D(50)
    assert result.equity_curve.iloc[-1] == D(10050)


def test_swing_policy_honors_source_close_without_waiting_for_protection():
    result, _, trace = execute(
        [(100, 110, 90, 100), (100, 110, 91, 100), (100, 105, 95, 100), (102, 105, 98, 100)],
        {1: {"action": "long"}, 2: {"action": "close"}},
    )
    assert result.trades[0].exit_price == D(102)
    assert fills(trace)[-1]["exit_reason"] == "source_close"


def test_reentry_funding_and_both_cost_legs_precede_new_compound_quantity():
    bars = [(100, 110, 90, 100), (100, 110, 91, 100), (100, 117, 100, 117), (112, 113, 111, 112)]
    rates = pd.Series([D("0.001")], index=frame(bars).index[3:])
    config = cfg(
        include_funding=True,
        fees=D("0.0002"),
        slippage=D("0.0001"),
        maker_fee=D("0.0001"),
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100,
    )
    result, _, trace = execute(
        bars,
        {1: {"action": "long"}, 2: {"action": "long"}},
        config=config,
        funding_rates=rates,
    )
    events = fills(trace)
    funding = next(row for row in trace if row["type"] == "funding")
    assert D(funding["amount"]) == D("5.600")
    expected_cash = D(10000)
    for row in events[:-1]:
        expected_cash += D(row.get("gross_pnl", "0")) - D(row["fee"]) - D(row["slippage"])
    expected_cash -= D(funding["amount"])
    assert D(events[-1]["quantity"]) == expected_cash / D(112)
    assert result.metrics.total_funding == D("5.600")


def test_shared_tape_reuses_actual_source_execution_and_keeps_same_signal_hash():
    bars = [(100, 110, 90, 100), (100, 110, 91, 100), (100, 117, 100, 117), (112, 113, 111, 112)]
    output: list[dict[str, Any]] = []
    _, transport, trace_a = execute(
        bars,
        {1: {"action": "long"}, 2: {"action": "long"}},
        research=policy("signal_only_v1"),
        signal_output=output,
    )
    assert all(row["position"]["direction"] == "flat" for row in transport.messages[1:])

    def forbidden_transport():
        pytest.fail("검증된 tape 재생은 소스를 다시 실행하지 않습니다")

    trace_b: list[dict[str, Any]] = []
    run_code_backtest(
        "reviewed source",
        "python",
        frame(bars),
        cfg(),
        research_policy=policy(),
        signal_tape=output,
        transport_factory=forbidden_transport,
        trace=trace_b,
    )
    assert trace_a[-1]["signal_hash"] == trace_b[-1]["signal_hash"]
    assert len(output) == len(bars)
    assert any(row["kind"] == "partial_tp" for row in fills(trace_b))
    assert not any(row["kind"] == "partial_tp" for row in fills(trace_a))


@pytest.mark.parametrize("change", ["mapping", "bar", "event", "duplicate", "length"])
def test_tape_with_different_inputs_or_repeated_event_is_rejected(change):
    bars = [(100, 110, 90, 100)] * 4
    output: list[dict[str, Any]] = []
    execute(bars, {1: {"action": "long"}, 2: {"action": "long"}}, signal_output=output)
    selected = policy()
    tape = deepcopy(output)
    if change == "mapping":
        selected = policy(signal_mapping_hash="b" * 64)
    elif change == "bar":
        bars[0] = (100, 111, 90, 100)
    elif change == "event":
        tape[1]["action"] = "short"
    elif change == "duplicate":
        tape[2]["event_id"] = tape[1]["event_id"]
    else:
        tape.pop()
    with pytest.raises(CodeRuntimeError, match="tape"):
        run_code_backtest(
            "reviewed source",
            "python",
            frame(bars),
            cfg(),
            research_policy=selected,
            signal_tape=tape,
        )


def test_feedback_source_observes_actual_position_and_cannot_replay_shared_tape():
    _, transport, trace = execute(
        [(100, 110, 90, 100)] * 4,
        {1: {"action": "long"}, 2: {"action": "close"}},
        research=policy(signal_mode="position_feedback"),
    )
    assert transport.messages[3]["position"]["direction"] == "long"
    assert trace[-1]["policy"]["signal_mode"] == "position_feedback"
    with pytest.raises(CodeRuntimeError, match="shared_events"):
        execute(
            [(100, 110, 90, 100)] * 4,
            {},
            research=policy(signal_mode="position_feedback"),
            signal_tape=[],
        )


def test_warmup_events_do_not_trade_and_last_signal_stays_unfilled():
    result, _, trace = execute(
        [(100, 110, 90, 100)] * 4,
        {0: {"action": "long"}, 1: {"action": "long"}, 3: {"action": "short"}},
        warmup_bars=2,
    )
    assert result.trades == []
    assert len(result.equity_curve) == 2
    intents = [row for row in trace if row["type"] == "intent"]
    assert [row["disposition"] for row in intents] == [
        "warmup",
        "warmup",
        "hold",
        "queued_unfilled",
    ]


def test_queued_reentry_precedes_old_protection_and_new_plan_uses_its_own_generation():
    _, _, trace = execute(
        [(100, 110, 90, 100), (100, 110, 91, 100), (100, 105, 95, 100), (100, 105, 80, 100)],
        {1: {"action": "long"}, 2: {"action": "long"}},
    )
    events = fills(trace)
    assert [(row["kind"], row["episode_id"]) for row in events] == [
        ("entry", 1),
        ("close", 1),
        ("entry", 2),
        ("stop_loss", 2),
    ]
    assert events[1]["exit_reason"] == "same_direction_reentry"
    assert D(events[3]["price"]) == D("90.10")


def test_protective_exit_stays_flat_until_a_distinct_new_event():
    result, _, trace = execute(
        [
            (100, 110, 90, 100),
            (100, 110, 91, 100),
            (100, 105, 80, 100),
            (100, 105, 95, 100),
            (100, 105, 95, 100),
        ],
        {1: {"action": "long"}},
    )
    assert len(result.trades) == 1
    assert [row["kind"] for row in fills(trace)] == ["entry", "stop_loss"]
    assert result.trades[0].status == "closed"


def test_invalid_swing_records_rejected_entry_without_restoring_closed_position():
    result, _, trace = execute(
        [(100, 110, 90, 100), (100, 110, 91, 100), (100, 105, 95, 100), (80, 85, 75, 80)],
        {1: {"action": "long"}, 2: {"action": "long"}},
    )
    assert [row["kind"] for row in fills(trace)] == ["entry", "close"]
    assert result.trades[0].status == "closed"
    assert trace[-1]["counters"]["invalid_swing"] == 1
    assert [row["disposition"] for row in trace if row["type"] == "execution"] == [
        "entry",
        "invalid_swing",
    ]


@pytest.mark.parametrize("generation,quantity", [(0, D(1)), (1, D(11))])
def test_research_ledger_rejects_stale_generation_and_excess_remaining(generation, quantity):
    ledger = _Ledger(cfg(), D(10000), "source")
    ledger.market("long", D(100), 0, "start", "bar_open", [], signal_event_id="entry")
    with pytest.raises(ValueError, match="세대 또는 잔량"):
        ledger.exit(RiskEvent(generation, "close", D(100), quantity), 1, "end", "bar_open")
    assert ledger.remaining_qty == D(10)

"""부분 청산·예약·취소·활성화의 독립 수량/비용 반증 계약."""

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine import BacktestConfig, run_backtest
from src.strategy.pine_v2.exit_orders import ExitOrderKind
from src.strategy.pine_v2.strategy_state import MarketIntent, StrategyState


def opened(direction="long", qty=10.0):
    state = StrategyState()
    state.entry("L", direction, qty=qty, bar=0, fill_price=100)
    return state


@pytest.mark.parametrize("direction", ["long", "short"])
def test_partial_tp_keeps_remaining_stop_and_conserves_quantity(direction):
    state = opened(direction)
    sign = 1 if direction == "long" else -1
    state.place_exit(
        from_entry="L",
        exit_id="TP",
        bar=0,
        limit=100 + sign * 15,
        stop=100 - sign * 10,
        qty_percent=50,
    )
    state.place_exit(from_entry="L", exit_id="SL", bar=0, stop=100 - sign * 10)
    fills = state.check_exit_fills(
        bar=1, open_=100, high=116 if sign == 1 else 101, low=99 if sign == 1 else 84
    )
    assert len(fills) == 1 and fills[0].qty == 5
    assert state.open_trades["L"].qty == 5
    assert {leg.exit_id for leg in state.pending_exits["L"]} == {"SL"}
    fills = state.check_exit_fills(
        bar=2, open_=100, high=101 if sign == 1 else 111, low=89 if sign == 1 else 99
    )
    assert len(fills) == 1 and fills[0].qty == 5
    assert not state.open_trades and not state.pending_exits
    assert sum(trade.qty for trade in state.closed_trades) == 10
    assert sum(trade.pnl for trade in state.closed_trades) == 25
    assert [event.qty for event in state.events if event.action == "close"] == [5, 5]


def test_reservations_clamp_excess_and_same_id_reissue_replaces_only_own_group():
    state = opened()
    state.place_exit(from_entry="L", exit_id="A", bar=0, limit=110, qty=7)
    state.place_exit(from_entry="L", exit_id="B", bar=0, stop=90, qty=8)
    assert {leg.exit_id: leg.qty for leg in state.pending_exits["L"]} == {"A": 7, "B": 3}
    state.place_exit(from_entry="L", exit_id="A", bar=1, limit=120, qty=8)
    assert {leg.exit_id: leg.qty for leg in state.pending_exits["L"]} == {"A": 7, "B": 3}
    assert next(leg for leg in state.pending_exits["L"] if leg.exit_id == "A").limit_price == 120
    state.cancel("B")
    assert state.open_trades["L"].qty == 10
    state.place_exit(from_entry="L", exit_id="A", bar=2, limit=120, qty=8)
    assert state.pending_exits["L"][0].qty == 8


def test_multiple_stop_groups_can_fill_same_bar_without_overclose():
    state = opened()
    state.place_exit(from_entry="L", exit_id="A", bar=0, stop=90, qty=4)
    state.place_exit(from_entry="L", exit_id="B", bar=0, stop=90, qty=99)
    fills = state.check_exit_fills(bar=1, open_=100, high=101, low=89)
    assert [trade.qty for trade in fills] == [4, 6]
    assert sum(trade.pnl for trade in fills) == -100
    assert not state.open_trades


def test_cancel_removes_unfilled_orders_only_and_cancel_all_keeps_position():
    state = opened()
    state.entry("P", "long", qty=1, bar=0, fill_price=100, stop=120)
    state.place_exit(from_entry="L", exit_id="X", bar=0, stop=90)
    state.queue_market_intent(MarketIntent(kind="entry", trade_id="Q", qty=1))
    state.queue_market_intent(MarketIntent(kind="close", trade_id="L"))
    state.cancel("Q")
    assert [intent.trade_id for intent in state.pending_market_intents] == ["L"]
    state.cancel("X")
    assert not state.pending_exits and state.open_trades["L"].qty == 10
    state.cancel_all()
    assert not state.pending_orders and not state.pending_market_intents
    assert state.open_trades["L"].qty == 10 and not state.closed_trades


@pytest.mark.parametrize("direction", ["long", "short"])
def test_absolute_trail_activation_does_not_trigger_before_threshold(direction):
    state = opened(direction)
    state.place_exit(
        from_entry="L",
        exit_id="T",
        bar=0,
        trail_price=120 if direction == "long" else 80,
        trail_offset=5,
    )
    assert (
        state.check_exit_fills(
            bar=1,
            open_=105 if direction == "long" else 95,
            high=110 if direction == "long" else 97,
            low=103 if direction == "long" else 90,
        )
        == []
    )
    assert state.open_trades["L"].qty == 10
    assert (
        state.check_exit_fills(
            bar=2,
            open_=121 if direction == "long" else 79,
            high=122 if direction == "long" else 82,
            low=118 if direction == "long" else 78,
        )
        == []
    )
    state.place_exit(
        from_entry="L",
        exit_id="T",
        bar=2,
        trail_price=120 if direction == "long" else 80,
        trail_offset=5,
    )
    fills = state.check_exit_fills(
        bar=3,
        open_=119 if direction == "long" else 81,
        high=120 if direction == "long" else 84,
        low=116 if direction == "long" else 80,
    )
    assert len(fills) == 1 and fills[0].exit_price == (117 if direction == "long" else 83)
    assert fills[0].exit_kind == ExitOrderKind.TRAILING_STOP


def frame():
    return pd.DataFrame(
        {
            "open": [100] * 5,
            "high": [101, 101, 116, 101, 101],
            "low": [99, 99, 99, 99, 89],
            "close": [100] * 5,
            "volume": [1000] * 5,
        },
        index=pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC"),
    )


def test_partial_exit_ledger_preserves_entry_costs_exit_costs_funding_and_equity():
    source = """//@version=5
strategy("Partial contract")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
    strategy.exit("TP", "L", stop=90, limit=115, qty_percent=50)
    strategy.exit("SL", "L", stop=90)
"""
    candles = frame()
    rates = pd.Series([Decimal("0.01"), Decimal("0.01")], index=candles.index[[1, 3]], dtype=object)
    out = run_backtest(
        source,
        candles,
        BacktestConfig(
            init_cash=Decimal("1000"),
            fees=0.001,
            slippage=0.0005,
            maker_fee=0.0002,
            include_funding=True,
            freq="1h",
        ),
        funding_rates=rates,
    )
    assert out.status == "ok", out.error
    result = out.result
    assert result is not None and len(result.trades) == 2
    assert [trade.size for trade in result.trades] == [Decimal("5"), Decimal("5")]
    assert result.metrics.total_fees == Decimal("1.565")
    assert result.metrics.total_slippage == Decimal(".725")
    assert result.metrics.total_funding == Decimal("15")
    assert sum(trade.pnl for trade in result.trades) == Decimal("22.71")
    assert result.equity_curve.iloc[-1] == Decimal("1007.71")


def test_interpreter_cancel_and_cancel_all_keep_open_position():
    source = """//@version=5
strategy("Cancel contract")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
    strategy.exit("X", "L", limit=115)
    strategy.cancel("X")
    strategy.entry("P", strategy.long, qty=1, stop=105)
    strategy.cancel_all()
"""
    out = run_backtest(source, frame(), BacktestConfig(fees=0, slippage=0))
    assert out.status == "ok", out.error
    assert len(out.result.trades) == 1 and out.result.trades[0].status == "open"
    assert out.result.trades[0].size == Decimal("10")


def test_unsupported_exit_kwargs_are_not_silently_ignored():
    source = """//@version=5
strategy("Unsupported exit")
strategy.entry("L", strategy.long)
strategy.exit("X", "L", stop=90, oca_name="custom")
"""
    out = run_backtest(source, frame(), BacktestConfig())
    assert out.status != "ok"
    assert "oca_name" in str(out.error)


@pytest.mark.parametrize("feature", ["partial", "activation", "cancel", "multi"])
def test_advanced_exits_fail_closed_in_live_surface(feature):
    from src.strategy.pine_v2.event_loop import run_live

    orders = {
        "partial": 'strategy.exit("X", "L", limit=115, qty_percent=50)',
        "activation": 'strategy.exit("X", "L", trail_price=120, trail_offset=5)',
        "cancel": 'strategy.cancel("X")',
        "multi": 'strategy.exit("X", "L", limit=115, qty=5)\n    strategy.exit("Y", "L", stop=90)',
    }
    source = f"""//@version=5
strategy("Live unsupported exit")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
    strategy.entry("P", strategy.long, qty=1, stop=130)
    {orders[feature]}
"""
    live = run_live(source, frame().iloc[:1])
    assert live.signals == [] and live.pending_orders == []
    assert any("advanced_exit_unsupported_live" in message for _, message in live.errors)
    assert any(
        row["reason"] == "advanced_exit_unsupported_live"
        for row in live.strategy_state_report["pending_order_skips"]
    )


def test_live_blocks_advanced_exit_before_its_branch_first_runs():
    from src.strategy.pine_v2.event_loop import run_live

    source = """//@version=5
strategy("Future partial")
strategy.entry("L", strategy.long, qty=10)
if bar_index > 10
    strategy.exit("X", "L", limit=115, qty_percent=50)
"""
    live = run_live(source, frame().iloc[:1])
    assert live.signals == [] and live.pending_orders == []
    assert any("advanced_exit_unsupported_live" in message for _, message in live.errors)


def test_fractional_partial_preserves_decimal_quantity_and_margin():
    state = opened(qty=0.3)
    state.open_trades["L"].margin_used = 3.0
    state.place_exit(from_entry="L", exit_id="X", bar=0, limit=110, qty=0.1, qty_percent=80)
    fills = state.check_exit_fills(bar=1, open_=100, high=111, low=99)
    assert Decimal(str(fills[0].qty)) == Decimal("0.1")
    assert Decimal(str(state.open_trades["L"].qty)) == Decimal("0.2")
    assert fills[0].margin_used == 1.0
    assert state.open_trades["L"].margin_used == 2.0


def test_partial_tp_open_leg_allocates_entry_cost_once():
    source = """//@version=5
strategy("Open partial")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
    strategy.exit("TP", "L", limit=115, qty_percent=50)
"""
    candles = frame().iloc[:3]
    rates = pd.Series([Decimal("0.01")], index=candles.index[[1]], dtype=object)
    out = run_backtest(
        source,
        candles,
        BacktestConfig(
            init_cash=Decimal("1000"),
            fees=0.001,
            slippage=0.0005,
            maker_fee=0.0002,
            include_funding=True,
            freq="1h",
        ),
        funding_rates=rates,
    )
    assert out.status == "ok", out.error
    result = out.result
    assert sorted((trade.status, trade.size) for trade in result.trades) == [
        ("closed", Decimal("5")),
        ("open", Decimal("5")),
    ]
    assert result.metrics.total_fees == Decimal("1.115")
    assert result.metrics.total_slippage == Decimal("0.5")
    assert result.metrics.total_funding == Decimal("10")
    assert result.equity_curve.iloc[-1] == Decimal("1063.385")


@pytest.mark.parametrize(
    "arguments",
    [
        "trail_price=120, trail_points=5",
        "qty_percent=-1, limit=115",
    ],
)
def test_invalid_or_ambiguous_exit_parameters_fail_explicitly(arguments):
    source = f"""//@version=5
strategy("Invalid partial")
strategy.entry("L", strategy.long)
strategy.exit("X", "L", {arguments})
"""
    out = run_backtest(source, frame(), BacktestConfig())
    assert out.status != "ok"


def test_legacy_trail_points_offset_combo_preserves_fills_with_explicit_warning():
    source = """//@version=5
strategy("Legacy trail")
if bar_index == 0
    strategy.entry("L", strategy.long)
    strategy.exit("X", "L", trail_points=20, trail_offset=5)
"""
    out = run_backtest(source, frame(), BacktestConfig())
    equivalent = run_backtest(source.replace("trail_points=20, ", ""), frame(), BacktestConfig())
    assert out.status == equivalent.status == "ok"
    assert out.result.trades == equivalent.result.trades
    assert any("activation" in warning for warning in out.parse.warnings)


@pytest.mark.parametrize("direction", ["long", "short"])
def test_new_absolute_activation_cannot_fill_at_pre_activation_open(direction):
    state = opened(direction)
    state.place_exit(
        from_entry="L",
        exit_id="T",
        bar=0,
        trail_price=120 if direction == "long" else 80,
        trail_offset=20,
    )
    fills = state.check_exit_fills(
        bar=1,
        open_=100,
        high=125 if direction == "long" else 101,
        low=99 if direction == "long" else 75,
    )
    assert len(fills) == 1
    assert fills[0].exit_price == (105 if direction == "long" else 95)


@pytest.mark.parametrize("entry_expression", ['""', "entryName"])
def test_live_blocks_future_overlapping_exit_ids_with_wildcard_or_dynamic_entry(entry_expression):
    from src.strategy.pine_v2.event_loop import run_live

    source = f"""//@version=5
strategy("Future overlapping exits")
entryName = "L"
strategy.entry("L", strategy.long, qty=10)
if bar_index > 10
    strategy.exit("A", from_entry={entry_expression}, limit=115)
    strategy.exit("B", "L", stop=90)
"""
    live = run_live(source, frame().iloc[:1])
    assert live.signals == [] and live.pending_orders == []
    assert any("advanced_exit_unsupported_live" in message for _, message in live.errors)


@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("prior_state", ["inactive", "active", "active_gap"])
def test_absolute_trail_distinguishes_open_gap_from_later_ratchet(direction, prior_state):
    state = opened(direction)
    is_long = direction == "long"
    state.place_exit(
        from_entry="L",
        exit_id="T",
        bar=0,
        trail_price=120 if is_long else 80,
        trail_offset=5,
    )
    if prior_state != "inactive":
        assert (
            state.check_exit_fills(
                bar=1,
                open_=123 if is_long else 77,
                high=125 if is_long else 79,
                low=121 if is_long else 75,
            )
            == []
        )
    is_gap = prior_state == "active_gap"
    open_price = (115 if is_long else 85) if is_gap else (125 if is_long else 75)
    fills = state.check_exit_fills(
        bar=2,
        open_=open_price,
        high=150 if is_long else (90 if is_gap else 79),
        low=(110 if is_gap else 121) if is_long else 50,
    )
    assert len(fills) == 1
    assert fills[0].exit_price == (open_price if is_gap else (145 if is_long else 55))


@pytest.mark.parametrize("id_argument", ["exitName", "id=exitName"])
def test_live_blocks_single_dynamic_exit_id_before_first_entry(id_argument):
    from src.strategy.pine_v2.event_loop import run_live

    source = f"""//@version=5
strategy("Dynamic exit ID")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=10)
exitName = bar_index > 1 ? "A" : "B"
strategy.exit({id_argument}, from_entry="L", stop=90)
"""
    live = run_live(source, frame().iloc[:1])
    assert live.signals == [] and live.pending_orders == []
    assert any("advanced_exit_unsupported_live" in message for _, message in live.errors)

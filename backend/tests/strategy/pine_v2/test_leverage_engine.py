# Pine v2 레버리지 마진 게이트와 격리 강제청산 엔진 회귀 테스트.
from __future__ import annotations

import pytest

from src.strategy.pine_v2.strategy_state import StrategyState


def _state(*, leverage: float = 1.0, initial_capital: float = 1000.0) -> StrategyState:
    state = StrategyState()
    state.configure_sizing(initial_capital=initial_capital, leverage=leverage)
    return state


def test_one_x_is_noop_for_margin_and_liquidation() -> None:
    state = _state()

    trade = state.entry("L", "long", qty=10.0, bar=0, fill_price=100.0)

    assert trade is not None
    assert trade.liq_price is None
    assert trade.margin_used is None
    assert state.check_liquidations(bar=1, open_=90.0, high=95.0, low=1.0) == []


def test_liquidation_prices_and_triggers_for_both_directions() -> None:
    long_state = _state(leverage=10.0)
    long_trade = long_state.entry("L", "long", qty=1.0, bar=0, fill_price=100.0)
    assert long_trade is not None
    assert long_trade.liq_price == pytest.approx(90.5)
    assert long_state.check_liquidations(bar=1, open_=95.0, high=96.0, low=91.0) == []
    liquidated_long = long_state.check_liquidations(
        bar=2, open_=95.0, high=96.0, low=90.0
    )
    assert liquidated_long[0].exit_price == pytest.approx(90.5)
    assert liquidated_long[0].liquidated
    assert long_state.liquidation_count == 1

    short_state = _state(leverage=10.0)
    short_trade = short_state.entry("S", "short", qty=1.0, bar=0, fill_price=100.0)
    assert short_trade is not None
    assert short_trade.liq_price == pytest.approx(109.5)
    liquidated_short = short_state.check_liquidations(
        bar=1, open_=105.0, high=110.0, low=104.0
    )
    assert liquidated_short[0].exit_price == pytest.approx(109.5)
    assert short_state.liquidation_count == 1


def test_liquidation_uses_gap_through_open_price() -> None:
    state = _state(leverage=10.0)
    state.entry("L", "long", qty=1.0, bar=0, fill_price=100.0)

    liquidated = state.check_liquidations(bar=1, open_=88.0, high=89.0, low=85.0)

    assert liquidated[0].exit_price == pytest.approx(88.0)


def test_liquidation_skips_entry_bar() -> None:
    state = _state(leverage=10.0)
    state.entry("L", "long", qty=1.0, bar=3, fill_price=100.0)

    assert state.check_liquidations(bar=3, open_=90.0, high=91.0, low=80.0) == []
    assert "L" in state.open_trades


def test_margin_gate_skips_market_entry() -> None:
    state = _state(leverage=2.0)

    trade = state.entry("L", "long", qty=20.0, bar=0, fill_price=100.0)

    assert trade is None
    assert "L" not in state.open_trades
    assert any("증거금 부족으로 진입 skip" in warning for warning in state.warnings)


def test_margin_gate_skips_stop_fill_and_removes_pending_order() -> None:
    state = _state(leverage=2.0)
    state.entry("L", "long", qty=20.0, bar=0, fill_price=100.0, stop=101.0)

    filled = state.check_pending_fills(bar=1, open_=100.0, high=102.0, low=99.0)

    assert filled == []
    assert "L" not in state.open_trades
    assert "L" not in state.pending_orders
    assert any("증거금 부족으로 진입 skip" in warning for warning in state.warnings)


def test_margin_gate_subtracts_open_position_margin() -> None:
    state = _state(leverage=2.0)

    first = state.entry("L1", "long", qty=10.0, bar=0, fill_price=100.0)
    second = state.entry("L2", "long", qty=10.0, bar=1, fill_price=100.0)

    assert first is not None
    assert first.margin_used == pytest.approx(500.0)
    assert second is None


def test_margin_gate_does_not_mutate_running_equity() -> None:
    state = _state(leverage=2.0)
    running_equity = state.running_equity

    state.entry("L", "long", qty=20.0, bar=0, fill_price=100.0)

    assert state.running_equity == running_equity


def test_margin_preflight_keeps_same_id_position_open_when_replacement_is_rejected() -> None:
    state = _state(leverage=2.0)
    original = state.entry("L", "long", qty=10.0, bar=0, fill_price=100.0)

    replacement = state.entry("L", "long", qty=20.0, bar=1, fill_price=100.0)

    assert original is not None
    assert replacement is None
    assert state.open_trades == {"L": original}
    assert state.closed_trades == []


def test_margin_preflight_allows_flip_after_releasing_margin_and_realizing_pnl() -> None:
    state = _state(leverage=2.0)
    original = state.entry("L", "long", qty=10.0, bar=0, fill_price=100.0)

    flipped = state.entry("S", "short", qty=19.0, bar=1, fill_price=200.0)

    assert original is not None
    assert flipped is not None
    assert original.pnl == pytest.approx(1000.0)
    assert flipped.margin_used == pytest.approx(1900.0)
    assert state.running_equity == pytest.approx(2000.0)


def test_margin_preflight_keeps_opposite_position_open_when_stop_fill_is_rejected() -> None:
    state = _state(leverage=2.0)
    original = state.entry("L", "long", qty=10.0, bar=0, fill_price=100.0)
    state.entry("S", "short", qty=20.0, bar=0, fill_price=100.0, stop=101.0)

    filled = state.check_pending_fills(bar=1, open_=100.0, high=102.0, low=99.0)

    assert original is not None
    assert filled == []
    assert state.open_trades == {"L": original}
    assert state.closed_trades == []
    assert "S" not in state.pending_orders

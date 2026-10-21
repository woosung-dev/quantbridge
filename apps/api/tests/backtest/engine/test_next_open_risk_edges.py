"""시가 시장가의 반전 사이징·진입봉 위험과 기존 체결 순서의 경계를 검증한다."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.strategy_state import MarketIntent, StrategyState


def _candles(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": prices,
            "high": [price + 1 for price in prices],
            "low": [price - 1 for price in prices],
            "close": prices,
            "volume": 1,
        },
        index=pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC"),
    )


def _source(track: str, direction: str, *, flip: bool = False, explicit_exit: bool = False) -> str:
    opposite = "short" if direction == "long" else "long"
    if track == "S":
        source = (
            '//@version=5\nstrategy("Risk edges")\n'
            f'if bar_index == 0\n    strategy.entry("{direction}", strategy.{direction})\n'
        )
        if explicit_exit:
            source += f'if bar_index == 1\n    strategy.close("{direction}")\n'
        if flip:
            source += f'if bar_index == 1\n    strategy.entry("{opposite}", strategy.{opposite})\n'
        return source
    source = (
        '//@version=5\nindicator("Risk edges")\n'
        f'alertcondition(bar_index == 0, "{direction}", "{direction}")\n'
    )
    if explicit_exit:
        source += f'alertcondition(bar_index == 1, "Close {direction}", "close {direction}")\n'
    if flip:
        source += f'alertcondition(bar_index == 1, "{opposite}", "{opposite}")\n'
    return source


@pytest.mark.parametrize("track", ["A", "S"])
@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("exit_price", [50.0, 200.0])
def test_percent_reversal_matches_explicit_close_then_entry(
    track: str, direction: str, exit_price: float
) -> None:
    frame = _candles([100.0, 100.0, exit_price])
    config = BacktestConfig(
        init_cash=Decimal("1000"),
        fees=0,
        slippage=0,
        freq="1h",
        fill_timing="next_bar_open",
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=50.0,
    )
    results = []
    for explicit_exit in (False, True):
        outcome = run_backtest_v2(
            _source(track, direction, flip=True, explicit_exit=explicit_exit), frame, config
        )
        assert outcome.status == "ok", outcome.error
        assert outcome.result is not None
        results.append(outcome.result.trades)
    for trades in results:
        assert len(trades) == 2
        closed, opened = trades
        sign = Decimal("1") if direction == "long" else Decimal("-1")
        realized = (Decimal(str(exit_price)) - Decimal("100")) * Decimal("5") * sign
        expected_size = (Decimal("1000") + realized) / 2 / Decimal(str(exit_price))
        assert closed.status == "closed" and closed.pnl == realized
        assert closed.size == Decimal("5")
        assert closed.exit_bar_index == opened.entry_bar_index == 2
        assert opened.size == expected_size
    assert results[0] == results[1]


@pytest.mark.parametrize("track", ["A", "S"])
@pytest.mark.parametrize(
    ("qty_type", "qty_value", "expected"),
    [(None, None, "1"), ("strategy.cash", 500.0, "2.5"), ("strategy.fixed", 3.0, "3")],
)
def test_non_percent_reversal_keeps_default_quantity_contract(
    track: str, qty_type: str | None, qty_value: float | None, expected: str
) -> None:
    outcome = run_backtest_v2(
        _source(track, "long", flip=True),
        _candles([100.0, 100.0, 200.0]),
        BacktestConfig(
            fees=0,
            slippage=0,
            freq="1h",
            fill_timing="next_bar_open",
            default_qty_type=qty_type,
            default_qty_value=qty_value,
        ),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    assert outcome.result.trades[-1].size == Decimal(expected)


@pytest.mark.parametrize("track", ["A", "S"])
@pytest.mark.parametrize("direction", ["long", "short"])
def test_next_open_market_entry_is_exposed_to_entry_bar_liquidation(
    track: str, direction: str
) -> None:
    frame = _candles([100.0, 100.0])
    frame.loc[frame.index[1], ["high", "low"]] = [120.0, 80.0]
    outcome = run_backtest_v2(
        _source(track, direction),
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", leverage=10, fill_timing="next_bar_open"),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    (trade,) = outcome.result.trades
    assert trade.status == "closed" and trade.liquidated
    assert trade.entry_bar_index == trade.exit_bar_index == 1
    assert trade.exit_price is not None
    assert float(trade.exit_price) == pytest.approx(90.5 if direction == "long" else 109.5)
    assert float(trade.pnl) == pytest.approx(-9.5)


@pytest.mark.parametrize("track", ["A", "S"])
@pytest.mark.parametrize("direction", ["long", "short"])
def test_bar_close_entry_does_not_use_earlier_entry_bar_wicks(track: str, direction: str) -> None:
    frame = _candles([100.0, 100.0])
    frame.loc[frame.index[0], ["high", "low"]] = [120.0, 80.0]
    outcome = run_backtest_v2(
        _source(track, direction),
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", leverage=10),
    )
    assert outcome.status == "ok", outcome.error
    assert outcome.result is not None
    (trade,) = outcome.result.trades
    assert trade.status == "open" and not trade.liquidated
    assert trade.entry_bar_index == 0


@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("order_kind", ["stop", "limit"])
def test_intrabar_pending_entry_keeps_existing_entry_bar_order_assumption(
    direction: str, order_kind: str
) -> None:
    state = StrategyState()
    state.configure_sizing(initial_capital=1000, leverage=10)
    state.entry("T", direction, qty=1, bar=0, fill_price=100, **{order_kind: 100})
    open_price = 99 if (direction == "long") == (order_kind == "stop") else 101
    filled = state.check_pending_fills(bar=1, open_=open_price, high=120, low=80)
    assert len(filled) == 1
    assert state.check_liquidations(bar=1, open_=open_price, high=120, low=80) == []
    assert "T" in state.open_trades
    assert len(state.check_liquidations(bar=2, open_=100, high=120, low=80)) == 1


def test_default_percent_reversal_rejected_by_margin_keeps_original_position() -> None:
    state = StrategyState()
    state.configure_sizing(
        initial_capital=1000,
        leverage=2,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=250,
    )
    original = state.entry("L", "long", qty=10, bar=0, fill_price=100)
    assert original is not None
    state.queue_market_intent(MarketIntent(kind="entry", trade_id="S", direction="short"))
    state.process_market_intents(bar=1, open_=100)
    assert state.open_trades == {"L": original}
    assert state.closed_trades == []
    assert state.entry_skips[-1]["reason"] == "margin_insufficient"


def test_bankrupt_percent_reversal_does_not_open_negative_quantity() -> None:
    state = StrategyState()
    state.configure_sizing(
        initial_capital=1000,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100,
    )
    original = state.entry("S", "short", qty=10, bar=0, fill_price=100)
    assert original is not None
    state.queue_market_intent(MarketIntent(kind="entry", trade_id="L", direction="long"))
    state.process_market_intents(bar=1, open_=300)
    assert state.open_trades == {"S": original}
    assert state.closed_trades == []
    assert state.entry_skips[-1]["reason"] == "non_positive_equity"

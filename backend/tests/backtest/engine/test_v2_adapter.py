"""pine_v2 adapter 단위 — Decimal 합산, 수수료, equity/metrics 재구성."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import (
    _build_raw_trades,
    _compute_equity_curve,
    _compute_metrics,
    _detect_version,
)
from src.strategy.pine_v2.strategy_state import StrategyState, Trade


def _cfg(
    init: str = "10000", fees: float = 0.0, slippage: float = 0.0
) -> BacktestConfig:
    return BacktestConfig(init_cash=Decimal(init), fees=fees, slippage=slippage)


# --- _detect_version ---------------------------------------------------------


@pytest.mark.parametrize(
    "source,expected",
    [
        ("//@version=4\nstrategy('x')", "v4"),
        ("//@version=5\nstrategy('x')", "v5"),
        ("//@version=6\nstrategy('x')", "v5"),  # v6 은 v5 로 fallback
        ("strategy('x')", "v5"),  # 버전 명시 없음 → v5
    ],
)
def test_detect_version_parses_comment_annotation(source: str, expected: str) -> None:
    assert _detect_version(source) == expected


# --- _build_raw_trades -------------------------------------------------------


def _state_with_trades(*trades: Trade) -> StrategyState:
    st = StrategyState()
    for t in trades:
        if t.exit_bar is not None:
            st.closed_trades.append(t)
        else:
            st.open_trades[t.id] = t
    return st


def test_build_raw_trades_preserves_pnl_and_direction_with_zero_fees() -> None:
    state = _state_with_trades(
        Trade(
            id="L",
            direction="long",
            qty=1.0,
            entry_bar=1,
            entry_price=100.0,
            exit_bar=5,
            exit_price=110.0,
            pnl=10.0,
        )
    )
    trades = _build_raw_trades(state, _cfg())
    assert len(trades) == 1
    t = trades[0]
    assert t.direction == "long"
    assert t.status == "closed"
    assert t.entry_price == Decimal("100.0")
    assert t.exit_price == Decimal("110.0")
    assert t.size == Decimal("1.0")
    assert t.pnl == Decimal("10.0")
    assert t.return_pct == Decimal("10.0") / Decimal("100.0")
    assert t.fees == Decimal("0")


def test_build_raw_trades_applies_fees_and_slippage() -> None:
    state = _state_with_trades(
        Trade(
            id="L",
            direction="long",
            qty=2.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=3,
            exit_price=110.0,
            pnl=20.0,
        )
    )
    # fee 0.1% + slip 0.05% on each side of 2 unit @ (100 + 110) notional
    cfg = _cfg(fees=0.001, slippage=0.0005)
    trades = _build_raw_trades(state, cfg)
    t = trades[0]
    # expected fee = (100*2 + 110*2) * 0.001 + (100*2 + 110*2) * 0.0005
    #              = 420 * 0.0015 = 0.63
    assert t.fees == Decimal("0.63")
    # net pnl = 20 - 0.63
    assert t.pnl == Decimal("20") - Decimal("0.63")


def test_build_raw_trades_open_position_no_exit_price() -> None:
    state = _state_with_trades(
        Trade(
            id="L", direction="long", qty=1.0, entry_bar=2, entry_price=100.0,
        )
    )
    trades = _build_raw_trades(state, _cfg())
    assert len(trades) == 1
    assert trades[0].status == "open"
    assert trades[0].exit_price is None
    assert trades[0].exit_bar_index is None


def test_build_raw_trades_short_direction_pnl_sign() -> None:
    state = _state_with_trades(
        Trade(
            id="S",
            direction="short",
            qty=1.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=5,
            exit_price=90.0,
            # pnl 은 StrategyState 에서 이미 계산됨 (short → (entry - exit) * qty)
            pnl=10.0,
        )
    )
    trades = _build_raw_trades(state, _cfg())
    assert trades[0].pnl == Decimal("10.0")
    assert trades[0].direction == "short"


# --- _compute_equity_curve ---------------------------------------------------


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.5 for c in closes],
            "low": [c - 0.5 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


def test_equity_curve_accrues_realized_pnl_on_exit_bar() -> None:
    # Long 1.0 entry @ bar 0 price 100, exit @ bar 3 price 110 → +10 at bar 3.
    state = _state_with_trades(
        Trade(
            id="L",
            direction="long",
            qty=1.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=3,
            exit_price=110.0,
            pnl=10.0,
        )
    )
    trades = _build_raw_trades(state, _cfg())
    curve = _compute_equity_curve(trades, _ohlcv([100, 102, 105, 110, 108]), _cfg())
    # bar 0..2: unrealized by open trade → mark-to-market 따라가며 증가
    # bar 3: realized +10 — open 포지션 이미 청산됨 → 10010 이어야 함
    # bar 4: close 108 — 포지션 닫혀있어서 cash 만
    assert curve.iloc[0] == pytest.approx(10000.0)  # unrealized = (100-100)*1 = 0
    assert curve.iloc[1] == pytest.approx(10002.0)  # unrealized = (102-100)*1
    assert curve.iloc[3] == pytest.approx(10010.0)  # realized +10
    assert curve.iloc[4] == pytest.approx(10010.0)  # flat, cash만


def test_equity_curve_open_long_position_mark_to_market() -> None:
    state = _state_with_trades(
        Trade(
            id="L", direction="long", qty=2.0, entry_bar=1, entry_price=50.0,
        )
    )
    trades = _build_raw_trades(state, _cfg())
    curve = _compute_equity_curve(trades, _ohlcv([40, 50, 55, 60]), _cfg())
    # bar 0: entry 아직 안 됨 → cash 만
    assert curve.iloc[0] == pytest.approx(10000.0)
    # bar 1: entry 된 bar, close 50 → unrealized 0
    assert curve.iloc[1] == pytest.approx(10000.0)
    # bar 2: close 55 → unrealized (55-50)*2 = 10
    assert curve.iloc[2] == pytest.approx(10010.0)
    # bar 3: close 60 → unrealized (60-50)*2 = 20
    assert curve.iloc[3] == pytest.approx(10020.0)


# --- _compute_metrics --------------------------------------------------------


def test_metrics_no_trades_returns_zero_totals() -> None:
    cfg = _cfg()
    equity = pd.Series([10000.0, 10000.0, 10000.0])
    metrics = _compute_metrics([], equity, cfg)
    assert metrics.num_trades == 0
    assert metrics.total_return == Decimal("0")
    assert metrics.win_rate == Decimal("0")
    assert metrics.long_count == 0
    assert metrics.short_count == 0


def test_metrics_win_rate_from_closed_trades() -> None:
    cfg = _cfg()
    state = _state_with_trades(
        Trade(id="A", direction="long", qty=1.0, entry_bar=0, entry_price=100.0,
              exit_bar=1, exit_price=110.0, pnl=10.0),
        Trade(id="B", direction="long", qty=1.0, entry_bar=2, entry_price=100.0,
              exit_bar=3, exit_price=90.0, pnl=-10.0),
        Trade(id="C", direction="long", qty=1.0, entry_bar=4, entry_price=100.0,
              exit_bar=5, exit_price=105.0, pnl=5.0),
    )
    trades = _build_raw_trades(state, cfg)
    equity = pd.Series([10000.0, 10010.0, 10010.0, 10000.0, 10000.0, 10005.0])
    metrics = _compute_metrics(trades, equity, cfg)
    assert metrics.num_trades == 3
    # 2 wins / 3 = 0.666...
    assert metrics.win_rate == Decimal(2) / Decimal(3)
    assert metrics.long_count == 3
    assert metrics.short_count == 0
    assert metrics.profit_factor is not None
    # gross profit = 15, gross loss = 10 → PF = 1.5
    assert metrics.profit_factor == Decimal("15") / Decimal("10")

# exit-leg maker/taker 비용 split — TP=maker(slippage 면제), SL=taker, C14 불변식 보존.
"""T0-pine-oco C6 — exit-leg maker/taker cost split via _leg_cost SSOT (BL-104).

Trade.exit_kind 태그 → v2_adapter 가 exit leg fill_type 을 fill_type_for() 로 라우팅.
TP(maker) = maker_fee + slippage 면제. SL/Trail(taker) = taker_fee + slippage.
exit_kind=None(market close/flip) → taker (byte-identical 회귀 0).
C14 불변식: total_fees + total_slippage == Σ RawTrade.fees.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import _build_raw_trades
from src.strategy.pine_v2.exit_orders import ExitOrderKind
from src.strategy.pine_v2.strategy_state import StrategyState, Trade


def _state_with_trade(exit_kind: ExitOrderKind | None) -> StrategyState:
    st = StrategyState()
    t = Trade(
        id="L",
        direction="long",
        qty=1.0,
        entry_bar=0,
        entry_price=100.0,
        exit_bar=2,
        exit_price=110.0,
        pnl=10.0,
        exit_kind=exit_kind,
    )
    st.closed_trades.append(t)
    return st


def test_taker_exit_leg_includes_slippage() -> None:
    cfg = BacktestConfig(fees=0.001, slippage=0.0005)
    raw = _build_raw_trades(_state_with_trade(None), cfg)
    # entry: 100*0.001 + 100*0.0005 = 0.15. exit(taker): 110*0.001 + 110*0.0005 = 0.165.
    assert raw[0].fees == Decimal("0.315")


def test_tp_maker_exit_leg_exempts_slippage() -> None:
    cfg = BacktestConfig(fees=0.001, slippage=0.0005, maker_fee=0.0002)
    raw = _build_raw_trades(_state_with_trade(ExitOrderKind.TAKE_PROFIT), cfg)
    # entry(taker): 0.15. exit(maker): 110*0.0002 maker_fee + 0 slip = 0.022.
    assert raw[0].fees == Decimal("0.172")


def test_sl_taker_exit_leg_includes_slippage() -> None:
    cfg = BacktestConfig(fees=0.001, slippage=0.0005, maker_fee=0.0002)
    raw = _build_raw_trades(_state_with_trade(ExitOrderKind.STOP_LOSS), cfg)
    # SL = taker → entry 0.15 + exit 0.165 = 0.315.
    assert raw[0].fees == Decimal("0.315")


def test_c14_invariant_holds_with_tp_maker_exit_end_to_end() -> None:
    # C14 불변식: total_fees + total_slippage == Σ trade.fees (TP maker 라우팅 포함).
    source = """//@version=5
strategy("c14 exit")
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", "L", limit=105.0)
"""
    rows = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (102.0, 106.0, 101.0, 104.0),  # TP 105 fill
    ]
    ohlcv = pd.DataFrame(
        {
            "open": [r[0] for r in rows],
            "high": [r[1] for r in rows],
            "low": [r[2] for r in rows],
            "close": [r[3] for r in rows],
            "volume": [1000.0] * len(rows),
        },
        index=pd.date_range("2026-01-01", periods=len(rows), freq="1h", tz="UTC"),
    )
    out = run_backtest(source, ohlcv, BacktestConfig(fees=0.001, slippage=0.0005))
    assert out.status == "ok"
    assert out.result is not None
    m = out.result.metrics
    trades = out.result.trades
    # TP maker 라우팅이 실제로 발동했는지 확인.
    assert any(t.exit_kind == ExitOrderKind.TAKE_PROFIT for t in trades)
    # 불변식.
    assert m.total_fees is not None and m.total_slippage is not None
    assert m.total_fees + m.total_slippage == sum(t.fees for t in trades)

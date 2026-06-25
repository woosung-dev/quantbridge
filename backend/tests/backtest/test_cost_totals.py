# C14 정직성 — 백테스트 total_fees / total_slippage 헤드라인 집계 손계산 오라클
from __future__ import annotations

from decimal import Decimal

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import (
    _build_raw_trades,
    _compute_equity_curve,
    _compute_metrics,
)
from tests.fixtures.backtest_golden_minimal import (
    make_s1_ohlcv,
    make_s1_state,
    make_s2_ohlcv,
    make_s2_state,
)

# fees=0.1%, slippage=0.05% — AssumptionsCard 기본값과 동일.
_CFG = BacktestConfig(init_cash=Decimal("1000"), fees=0.001, slippage=0.0005, freq="1D")
_ZERO_CFG = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="1D")


def _metrics(make_state, make_ohlcv, cfg: BacktestConfig):
    state = make_state()
    ohlcv = make_ohlcv()
    trades = _build_raw_trades(state, cfg)
    equity = _compute_equity_curve(trades, ohlcv, cfg)
    metrics = _compute_metrics(trades, equity, cfg, ohlcv)
    return trades, metrics


def test_s1_total_fees_and_slippage_hand_oracle() -> None:
    # S1: long entry@100 exit@120 qty=1.
    # fees = (100+120)*0.001 = 0.22 / slippage = (100+120)*0.0005 = 0.11
    _, metrics = _metrics(make_s1_state, make_s1_ohlcv, _CFG)
    assert metrics.total_fees == Decimal("0.22")
    assert metrics.total_slippage == Decimal("0.11")


def test_s2_total_fees_and_slippage_hand_oracle() -> None:
    # S2: T1 long 100/120, T2 short 90/80.
    # fees = (220+170)*0.001 = 0.39 / slippage = (220+170)*0.0005 = 0.195
    _, metrics = _metrics(make_s2_state, make_s2_ohlcv, _CFG)
    assert metrics.total_fees == Decimal("0.39")
    assert metrics.total_slippage == Decimal("0.195")


def test_cost_split_invariant_equals_per_trade_fees() -> None:
    # drift 가드: total_fees + total_slippage == Σ RawTrade.fees (결합 per-trade 비용).
    # _build_raw_trades(결합) 와 _compute_metrics(분리) 가 독립 경로라 일관성 검증.
    trades, metrics = _metrics(make_s2_state, make_s2_ohlcv, _CFG)
    per_trade_total = sum((t.fees for t in trades), start=Decimal("0"))
    assert metrics.total_fees is not None and metrics.total_slippage is not None
    assert metrics.total_fees + metrics.total_slippage == per_trade_total


def test_zero_cost_config_yields_zero_not_none() -> None:
    # fees=0/slip=0 시 None 이 아니라 명시적 0 — 헤드라인에 "0 비용" 정직 표시.
    _, metrics = _metrics(make_s1_state, make_s1_ohlcv, _ZERO_CFG)
    assert metrics.total_fees == Decimal("0")
    assert metrics.total_slippage == Decimal("0")

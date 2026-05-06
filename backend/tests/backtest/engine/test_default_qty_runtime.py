# Pine default_qty_type/value 런타임 통합 회귀 (BL-185, Sprint 37 PR1 TDD-1.2bc/d).
"""BL-185 TDD-1.2bc/d RED — pine_v2 + v2_adapter 통합 e2e.

Sprint 37 PR1 acceptance 4:
a. percent_of_equity 30% 정확성 (running_equity 추적)
b. cash 100 USDT 고정 (BTC 가격 무관)
c. fixed 0.01 BTC 고정
d. 정직성 test: init_cash=10000 vs init_cash=50000 → 동일 strategy → 비율 일치

Layer 검증:
- v2_adapter.run_backtest_v2 → compat.parse_and_run_v2 → run_historical/run_virtual_strategy
- interpreter.py strategy.entry qty fallback → state.compute_qty
- virtual_strategy.py:142 qty=1.0 → state.compute_qty
- StrategyState.configure_sizing(initial_capital, default_qty_type, default_qty_value)

fees=0 / slippage=0 가정 (PR1 acceptance — fee/slippage 정확성 후속 TODO).
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2


def _ramp_ohlcv(prices: list[float]) -> pd.DataFrame:
    """단순 OHLCV — close=open=high=low=각 가격, volume=1.0."""
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1.0] * len(prices),
            "timestamp": pd.date_range("2025-01-01", periods=len(prices), freq="D", tz="UTC"),
        }
    )


def _zero_fee_config(init_cash: Decimal = Decimal("10000")) -> BacktestConfig:
    """fees=0 / slippage=0 — TDD-1.2 acceptance 단순화 (후속 TODO)."""
    return BacktestConfig(init_cash=init_cash, fees=0.0, slippage=0.0)


# Track A (indicator + alertcondition) 으로 검증 — 단순한 cross signal.
# Pine strategy() 보다 indicator() 가 setup 가벼움.
# 단, default_qty_type/value 는 strategy() 만 지원 → Track S 필요.
_STRATEGY_PERCENT_30 = '''//@version=5
strategy("PCT30", overlay=true,
  default_qty_type=strategy.percent_of_equity, default_qty_value=30)

if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 3
    strategy.close("L")
'''

_STRATEGY_CASH_100 = '''//@version=5
strategy("CASH100", overlay=true,
  default_qty_type=strategy.cash, default_qty_value=100)

if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 3
    strategy.close("L")
'''

_STRATEGY_FIXED_001 = '''//@version=5
strategy("FIXED", overlay=true,
  default_qty_type=strategy.fixed, default_qty_value=0.01)

if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 3
    strategy.close("L")
'''


def test_percent_of_equity_30pct_qty_at_entry() -> None:
    """percent_of_equity 30% / init_cash=10000 / fill_price=100 → entry qty=30."""
    ohlcv = _ramp_ohlcv([100.0, 100.0, 100.0, 100.0, 100.0])
    outcome = run_backtest_v2(_STRATEGY_PERCENT_30, ohlcv, _zero_fee_config())
    assert outcome.status == "ok", f"backtest 실패: {outcome.error}"
    assert outcome.result is not None
    trades = outcome.result.trades
    assert len(trades) == 1, f"trades 개수 1 기대: {len(trades)}"
    # 30% × 10000 / 100 = 30
    assert trades[0].size == pytest.approx(Decimal("30")), (
        f"percent_of_equity qty 부정확: {trades[0].size}"
    )


def test_cash_100usdt_qty_at_entry() -> None:
    """cash 100 USDT / fill_price=50 → qty=2."""
    ohlcv = _ramp_ohlcv([50.0, 50.0, 50.0, 50.0, 50.0])
    outcome = run_backtest_v2(_STRATEGY_CASH_100, ohlcv, _zero_fee_config())
    assert outcome.status == "ok", f"backtest 실패: {outcome.error}"
    assert outcome.result is not None
    trades = outcome.result.trades
    assert len(trades) == 1
    # 100 / 50 = 2
    assert trades[0].size == pytest.approx(Decimal("2")), (
        f"cash qty 부정확: {trades[0].size}"
    )


def test_fixed_001_qty_at_entry() -> None:
    """fixed 0.01 / fill_price 무관 → qty=0.01."""
    ohlcv = _ramp_ohlcv([100.0, 100.0, 100.0, 100.0, 100.0])
    outcome = run_backtest_v2(_STRATEGY_FIXED_001, ohlcv, _zero_fee_config())
    assert outcome.status == "ok", f"backtest 실패: {outcome.error}"
    assert outcome.result is not None
    trades = outcome.result.trades
    assert len(trades) == 1
    assert trades[0].size == pytest.approx(Decimal("0.01"))


def test_initial_capital_scales_proportionally() -> None:
    """정직성 test — init_cash=10000 vs 50000, percent_of_equity 30% → qty 비율 정확히 5x.

    핵심 검증: BL-185 spot-equivalent 가정의 정합성 (사용자 통찰).
    """
    ohlcv = _ramp_ohlcv([100.0, 100.0, 100.0, 100.0, 100.0])

    out_10k = run_backtest_v2(
        _STRATEGY_PERCENT_30, ohlcv, _zero_fee_config(Decimal("10000"))
    )
    out_50k = run_backtest_v2(
        _STRATEGY_PERCENT_30, ohlcv, _zero_fee_config(Decimal("50000"))
    )
    assert out_10k.status == "ok" and out_50k.status == "ok"
    assert out_10k.result is not None and out_50k.result is not None

    qty_10k = out_10k.result.trades[0].size
    qty_50k = out_50k.result.trades[0].size
    # 50k / 10k = 5x 비율 정확
    assert qty_50k == pytest.approx(qty_10k * Decimal("5")), (
        f"init_cash 비례 정확성 위반: 10k→qty={qty_10k}, 50k→qty={qty_50k}, "
        f"기대 비율 5x"
    )


def test_qty_one_fallback_when_no_default_qty() -> None:
    """default_qty_* 미지정 strategy → 기존 qty=1.0 fallback (회귀 안전성)."""
    source = '''//@version=5
strategy("NoQty", overlay=true)

if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 3
    strategy.close("L")
'''
    ohlcv = _ramp_ohlcv([100.0, 100.0, 100.0, 100.0, 100.0])
    outcome = run_backtest_v2(source, ohlcv, _zero_fee_config())
    assert outcome.status == "ok"
    assert outcome.result is not None
    trades = outcome.result.trades
    assert len(trades) == 1
    # default_qty_* 미지정 + configure_sizing 호출되어도 type=None → qty=1.0
    assert trades[0].size == pytest.approx(Decimal("1")), (
        f"default 미지정 fallback 실패: qty={trades[0].size}"
    )

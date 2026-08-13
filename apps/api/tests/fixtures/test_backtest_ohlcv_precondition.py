"""Sprint 25 BL-112 — backtest_ohlcv fixture 자체의 trade 발생 보장 precondition.

codex G.0 iter 2 가 발견: plan v2 의 "기존 fixture 재사용" 이 코드 실측으로 refuted
(num_trades=0). 따라서 본 precondition 이 GREEN 이어야 `test_auto_dogfood:scenario2`
의 `num_trades >= 1` assert 가 의미 있음.

vectorbt engine / pine_v2 변경 시 본 test 가 RED 면 fixture 조정 의무.
"""
from __future__ import annotations

from decimal import Decimal

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from tests.fixtures.backtest_ohlcv import (
    EMA_CROSS_PINE_SOURCE,
    make_trending_ohlcv,
)


def test_ema_cross_fixture_yields_at_least_three_trades() -> None:
    """make_trending_ohlcv() + EMA_CROSS_PINE_SOURCE → num_trades >= 3 보장.

    Sprint 25 Phase 3 코드 실측 baseline: num_trades = 3 (8 segments × 25 bars).
    vectorbt 또는 pine_v2 변경 시 segment 패턴 (linspace targets) 조정 필요.
    """
    out = run_backtest_v2(
        EMA_CROSS_PINE_SOURCE,
        make_trending_ohlcv(),
        BacktestConfig(init_cash=Decimal("10000")),
    )
    assert out.status == "ok", f"backtest status={out.status}, error={out.error}"
    assert out.result is not None, "BacktestResult missing despite ok status"
    assert out.result.metrics.num_trades >= 3, (
        f"fixture broken — num_trades={out.result.metrics.num_trades}, "
        f"expected >= 3. fixture (8-segment linspace) 조정 필요."
    )


def test_ema_cross_fixture_equity_curve_full_length() -> None:
    """equity_curve 가 모든 bar 에 대해 산출됐는지 검증."""
    ohlcv = make_trending_ohlcv(200)
    out = run_backtest_v2(
        EMA_CROSS_PINE_SOURCE,
        ohlcv,
        BacktestConfig(init_cash=Decimal("10000")),
    )
    assert out.result is not None
    assert len(out.result.equity_curve) == 200

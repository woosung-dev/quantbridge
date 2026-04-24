"""Walk-Forward degradation_ratio / aggregate 검증."""

from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import OVERFIT_PINE, make_trending_ohlcv


def test_degradation_ratio_with_real_run() -> None:
    ohlcv = make_trending_ohlcv(n_bars=400)
    result = run_walk_forward(
        OVERFIT_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50
    )
    # 타입 + aggregate 계산 일치 검증 (엔진 의존 값이 아닌 계산 규약).
    assert isinstance(result.degradation_ratio, Decimal)
    assert result.aggregate_oos_return == sum(
        (f.out_of_sample_return for f in result.folds),
        start=Decimal("0"),
    ) / Decimal(len(result.folds))

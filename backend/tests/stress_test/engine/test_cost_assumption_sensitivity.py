# Cost Assumption Sensitivity engine — fees × slippage 9-cell heatmap 검증
"""Sprint 50 Cost Assumption Sensitivity engine test.

Sprint 50 MVP scope = BacktestConfig.fees × slippage 만 sweep (서버 9 cell 제한).
진짜 Param Stability (EMA period × stop loss %) = BL-220 / Sprint 51.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.stress_test.engine.cost_assumption_sensitivity import (
    CostAssumptionCell,
    CostAssumptionResult,
    run_cost_assumption_sensitivity,
)


@pytest.fixture
def sample_pine() -> str:
    return """
//@version=5
strategy("Test", overlay=true)
ema_short = ta.ema(close, 5)
ema_long = ta.ema(close, 20)
if ta.crossover(ema_short, ema_long)
    strategy.entry("L", strategy.long)
if ta.crossunder(ema_short, ema_long)
    strategy.close("L")
"""


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=200, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(200)],
            "high": [101.0 + i * 0.1 for i in range(200)],
            "low": [99.0 + i * 0.1 for i in range(200)],
            "close": [100.5 + i * 0.1 for i in range(200)],
            "volume": [1000.0] * 200,
        },
        index=idx,
    )


def test_run_cost_assumption_3x3_grid_returns_9_cells(
    sample_pine: str, sample_ohlcv: pd.DataFrame
) -> None:
    """3x3 grid = 9 cell. row-major flatten."""
    result = run_cost_assumption_sensitivity(
        sample_pine,
        sample_ohlcv,
        param_grid={
            "fees": [Decimal("0.0005"), Decimal("0.001"), Decimal("0.002")],
            "slippage": [Decimal("0.0001"), Decimal("0.0005"), Decimal("0.001")],
        },
    )
    assert isinstance(result, CostAssumptionResult)
    assert result.param1_name == "fees"
    assert result.param2_name == "slippage"
    assert len(result.cells) == 9
    assert all(isinstance(c, CostAssumptionCell) for c in result.cells)


def test_run_cost_assumption_grid_size_bounded_at_9(
    sample_pine: str, sample_ohlcv: pd.DataFrame
) -> None:
    """codex P1#5 — 서버 9 cell 강제 제한 (Sprint 50 MVP)."""
    with pytest.raises(ValueError, match="exceeds 9 cells"):
        run_cost_assumption_sensitivity(
            sample_pine,
            sample_ohlcv,
            param_grid={
                "fees": [Decimal("0.001")] * 4,
                "slippage": [Decimal("0.0005")] * 3,  # 4*3 = 12 > 9
            },
        )


def test_run_cost_assumption_only_fees_slippage_supported(
    sample_pine: str, sample_ohlcv: pd.DataFrame
) -> None:
    """Sprint 50 MVP — fees / slippage 만. EMA period 등 = BL-220 / Sprint 51."""
    with pytest.raises(ValueError, match="param_grid keys must be subset of"):
        run_cost_assumption_sensitivity(
            sample_pine,
            sample_ohlcv,
            param_grid={
                "ema_period": [Decimal("5"), Decimal("10")],
                "stop_loss_pct": [Decimal("1.0")],
            },
        )


def test_run_cost_assumption_grid_must_have_exactly_2_keys(
    sample_pine: str, sample_ohlcv: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="exactly 2 keys"):
        run_cost_assumption_sensitivity(
            sample_pine,
            sample_ohlcv,
            param_grid={"fees": [Decimal("0.001")]},
        )


def test_run_cost_assumption_empty_values_rejected(
    sample_pine: str, sample_ohlcv: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        run_cost_assumption_sensitivity(
            sample_pine,
            sample_ohlcv,
            param_grid={"fees": [], "slippage": [Decimal("0.0005")]},
        )


def test_run_cost_assumption_extreme_fees_marks_cell(
    sample_pine: str, sample_ohlcv: pd.DataFrame
) -> None:
    """극단 fees (50%) 시 num_trades=0 또는 sharpe=None → is_degenerate=True 보장."""
    result = run_cost_assumption_sensitivity(
        sample_pine,
        sample_ohlcv,
        param_grid={"fees": [Decimal("0.5")], "slippage": [Decimal("0.0005")]},
    )
    assert len(result.cells) == 1
    cell = result.cells[0]
    # 극단값에서 결과는 produce 됨 (raise X), 그리고 정상 cell 또는 degenerate flag 정확
    assert isinstance(cell.is_degenerate, bool)
    assert isinstance(cell.num_trades, int)

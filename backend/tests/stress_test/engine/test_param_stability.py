# Param Stability engine 검증 — 9-cell grid + InputDecl cross-check (BL-220 Sprint 51 Slice 3)
"""Sprint 51 Slice 3 — engine param_stability.py 단위 검증.

Sprint 50 cost_assumption_sensitivity 패턴 1:1 재사용 + input_overrides 적용.
9-cell strict + var_name InputDecl cross-check + analyze_coverage pre-flight.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.stress_test.engine import (
    ParamStabilityCell,
    ParamStabilityResult,
    run_param_stability,
)

PINE_WITH_INPUTS = """
//@version=5
strategy("BL-220 test")
emaPeriod = input.int(14, "EMA Period")
stopLossPct = input.float(1.0, "Stop Loss %")
ema = ta.ema(close, emaPeriod)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""


def _make_ohlcv(n: int = 200) -> pd.DataFrame:
    """tz-aware DatetimeIndex OHLCV."""
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(n)],
            "high": [101.0 + i * 0.1 for i in range(n)],
            "low": [99.0 + i * 0.1 for i in range(n)],
            "close": [100.5 + i * 0.1 for i in range(n)],
            "volume": [1000.0] * n,
        },
        index=idx,
    )


class TestParamStability9CellGrid:
    """9-cell strict + result shape."""

    def test_3x3_grid_returns_9_cells(self) -> None:
        """3×3 grid → 9 cell + flatten row-major."""
        result = run_param_stability(
            PINE_WITH_INPUTS,
            _make_ohlcv(),
            param_grid={
                "emaPeriod": [Decimal("10"), Decimal("20"), Decimal("30")],
                "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
            },
        )
        assert isinstance(result, ParamStabilityResult)
        assert len(result.cells) == 9
        assert result.param1_name == "emaPeriod"
        assert result.param2_name == "stopLossPct"

    def test_4x3_grid_rejected_exceeds_9(self) -> None:
        """4×3 = 12 → ValueError raise (서버 9 cell 강제)."""
        with pytest.raises(ValueError, match="exceeds 9 cells"):
            run_param_stability(
                PINE_WITH_INPUTS,
                _make_ohlcv(),
                param_grid={
                    "emaPeriod": [
                        Decimal("10"),
                        Decimal("20"),
                        Decimal("30"),
                        Decimal("40"),
                    ],
                    "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
                },
            )

    def test_single_axis_rejected(self) -> None:
        """param_grid 1개 key → ValueError."""
        with pytest.raises(ValueError, match="exactly 2 keys"):
            run_param_stability(
                PINE_WITH_INPUTS,
                _make_ohlcv(),
                param_grid={"emaPeriod": [Decimal("10")]},
            )

    def test_empty_values_rejected(self) -> None:
        """빈 list → ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            run_param_stability(
                PINE_WITH_INPUTS,
                _make_ohlcv(),
                param_grid={"emaPeriod": [], "stopLossPct": [Decimal("1.0")]},
            )


class TestParamStabilityInputDeclCrossCheck:
    """codex G.0 edge case 1 — var_name InputDecl 부재 시 422 reject."""

    def test_unknown_var_name_rejected(self) -> None:
        """param_grid key 가 InputDecl 부재 → ValueError raise."""
        with pytest.raises(ValueError, match="not declared as pine input variables"):
            run_param_stability(
                PINE_WITH_INPUTS,
                _make_ohlcv(),
                param_grid={
                    "wrongKey": [Decimal("10"), Decimal("20")],
                    "stopLossPct": [Decimal("1.0"), Decimal("2.0")],
                },
            )


class TestParamStabilityCellMetrics:
    """cell metric 수집 — sharpe / total_return / max_drawdown / num_trades."""

    def test_cells_have_4_core_metrics(self) -> None:
        """매 cell 에 4 core metric + is_degenerate flag."""
        result = run_param_stability(
            PINE_WITH_INPUTS,
            _make_ohlcv(),
            param_grid={
                "emaPeriod": [Decimal("10"), Decimal("20")],
                "stopLossPct": [Decimal("1.0"), Decimal("2.0")],
            },
        )
        assert len(result.cells) == 4
        for cell in result.cells:
            assert isinstance(cell, ParamStabilityCell)
            assert cell.param1_value in (Decimal("10"), Decimal("20"))
            assert cell.param2_value in (Decimal("1.0"), Decimal("2.0"))
            # sharpe = None or Decimal (degenerate cell 시 None)
            assert cell.sharpe is None or isinstance(cell.sharpe, Decimal)
            assert isinstance(cell.total_return, Decimal)
            assert isinstance(cell.max_drawdown, Decimal)
            assert isinstance(cell.num_trades, int)
            assert isinstance(cell.is_degenerate, bool)


# NOTE: analyze_coverage pre-flight (미지원 builtin reject) path 는 Sprint 50
# cost_assumption_sensitivity 에서 동일 wrapper 로 이미 검증됨. Sprint 51 별도
# test 중복 회피 (Sprint Y1 trust layer 공통 path).

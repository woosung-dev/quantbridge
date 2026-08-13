"""BL-392 — CA/PS 공유 2D grid-sweep DTO 의 serializer round-trip 골든.

CA(Cost Assumption) 와 PS(Param Stability) 는 동일한 7-field grid-cell shape 를
공유한다 (`GridSweepMetricsResult`). 통합 serializer `grid_metrics_result_to_jsonb` /
`grid_metrics_result_from_jsonb` 가:
    - Decimal → str (JSON safe), None sharpe 보존, num_trades int / is_degenerate bool.
    - JSONB → schema 호환 dict (str 유지) → `GridSweepMetricsResultOut.model_validate`.
    - 구버전(통합 전 CA/PS) 저장 row 와 byte-identical → 하위호환 보장.
"""

from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine import GridSweepMetricsCell, GridSweepMetricsResult
from src.stress_test.schemas import GridSweepMetricsResultOut
from src.stress_test.serializers import (
    grid_metrics_result_from_jsonb,
    grid_metrics_result_to_jsonb,
)


def _make_result() -> GridSweepMetricsResult:
    """정상 cell + None-sharpe degenerate cell 혼합 2x1 grid."""
    return GridSweepMetricsResult(
        param1_name="fees",
        param2_name="slippage",
        param1_values=[Decimal("0.001"), Decimal("0.002")],
        param2_values=[Decimal("0.0005")],
        cells=[
            GridSweepMetricsCell(
                param1_value=Decimal("0.001"),
                param2_value=Decimal("0.0005"),
                sharpe=Decimal("1.25"),
                total_return=Decimal("0.30"),
                max_drawdown=Decimal("-0.10"),
                num_trades=12,
                is_degenerate=False,
            ),
            GridSweepMetricsCell(
                param1_value=Decimal("0.002"),
                param2_value=Decimal("0.0005"),
                sharpe=None,
                total_return=Decimal("0"),
                max_drawdown=Decimal("0"),
                num_trades=0,
                is_degenerate=True,
            ),
        ],
    )


def test_grid_metrics_to_jsonb_exact_shape() -> None:
    """to_jsonb: Decimal → str, None sharpe 보존, 정확한 JSONB shape."""
    jsonb = grid_metrics_result_to_jsonb(_make_result())
    assert jsonb == {
        "param1_name": "fees",
        "param2_name": "slippage",
        "param1_values": ["0.001", "0.002"],
        "param2_values": ["0.0005"],
        "cells": [
            {
                "param1_value": "0.001",
                "param2_value": "0.0005",
                "sharpe": "1.25",
                "total_return": "0.30",
                "max_drawdown": "-0.10",
                "num_trades": 12,
                "is_degenerate": False,
            },
            {
                "param1_value": "0.002",
                "param2_value": "0.0005",
                "sharpe": None,
                "total_return": "0",
                "max_drawdown": "0",
                "num_trades": 0,
                "is_degenerate": True,
            },
        ],
    }


def test_grid_metrics_roundtrip_to_out_schema() -> None:
    """to_jsonb → from_jsonb → GridSweepMetricsResultOut.model_validate round-trip."""
    jsonb = grid_metrics_result_to_jsonb(_make_result())
    restored = grid_metrics_result_from_jsonb(jsonb)
    out = GridSweepMetricsResultOut.model_validate(restored)

    assert out.param1_name == "fees"
    assert out.param2_name == "slippage"
    assert out.param1_values == ["0.001", "0.002"]
    assert out.param2_values == ["0.0005"]
    assert len(out.cells) == 2
    assert out.cells[0].sharpe == "1.25"
    assert out.cells[0].num_trades == 12
    assert out.cells[0].is_degenerate is False
    assert out.cells[1].sharpe is None
    assert out.cells[1].is_degenerate is True


def test_grid_metrics_from_jsonb_backward_compat_legacy_row() -> None:
    """통합 전 CA/PS 저장 row (동일 shape) 가 그대로 deserialize 되어야 (하위호환)."""
    legacy_stored = {
        "param1_name": "emaPeriod",
        "param2_name": "stopLossPct",
        "param1_values": ["10", "20"],
        "param2_values": ["0.5"],
        "cells": [
            {
                "param1_value": "10",
                "param2_value": "0.5",
                "sharpe": "0.80",
                "total_return": "0.15",
                "max_drawdown": "-0.05",
                "num_trades": 7,
                "is_degenerate": False,
            },
            {
                "param1_value": "20",
                "param2_value": "0.5",
                "sharpe": None,
                "total_return": "0",
                "max_drawdown": "0",
                "num_trades": 0,
                "is_degenerate": True,
            },
        ],
    }
    out = GridSweepMetricsResultOut.model_validate(
        grid_metrics_result_from_jsonb(legacy_stored)
    )
    assert out.param1_name == "emaPeriod"
    assert out.cells[0].num_trades == 7
    assert out.cells[1].sharpe is None

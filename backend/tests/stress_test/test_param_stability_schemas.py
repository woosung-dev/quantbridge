# Param Stability schema 검증 — 9-cell 강제 + empty 거부 + serialization (BL-220 Sprint 51)
"""Sprint 51 Slice 1 — ParamStabilityParams + Submit + Result schema."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.stress_test.schemas import (
    ParamStabilityCellOut,
    ParamStabilityParams,
    ParamStabilityResultOut,
    ParamStabilitySubmitRequest,
)


class TestParamStabilityParams:
    """9-cell 강제 + grid validator (Sprint 50 codex P1#5 패턴 재사용)."""

    def test_3x3_grid_accepted(self) -> None:
        """3×3 = 9-cell 정확히 통과."""
        params = ParamStabilityParams(
            param_grid={
                "emaPeriod": [Decimal("10"), Decimal("20"), Decimal("30")],
                "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
            }
        )
        assert len(params.param_grid["emaPeriod"]) == 3
        assert len(params.param_grid["stopLossPct"]) == 3

    def test_4x3_grid_rejected_exceeds_9(self) -> None:
        """4×3 = 12-cell 거부 (codex P1#5 9-cell 강제)."""
        with pytest.raises(ValueError, match="9 cells"):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": [
                        Decimal("10"),
                        Decimal("20"),
                        Decimal("30"),
                        Decimal("40"),
                    ],
                    "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
                }
            )

    def test_empty_values_rejected(self) -> None:
        """빈 list 거부."""
        with pytest.raises(ValueError, match="must not be empty"):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": [],
                    "stopLossPct": [Decimal("1.0")],
                }
            )

    def test_single_axis_rejected_min_length(self) -> None:
        """param_grid 1개 key 거부 (min_length=2 by Field constraint)."""
        with pytest.raises(ValueError):
            ParamStabilityParams(param_grid={"emaPeriod": [Decimal("10")]})

    def test_three_axis_rejected_max_length(self) -> None:
        """param_grid 3개 key 거부 (max_length=2)."""
        with pytest.raises(ValueError):
            ParamStabilityParams(
                param_grid={
                    "a": [Decimal("1")],
                    "b": [Decimal("2")],
                    "c": [Decimal("3")],
                }
            )


class TestParamStabilitySubmitRequest:
    """POST body 정합."""

    def test_submit_request_round_trip(self) -> None:
        """backtest_id + params 정상 round-trip."""
        backtest_id = uuid4()
        req = ParamStabilitySubmitRequest(
            backtest_id=backtest_id,
            params=ParamStabilityParams(
                param_grid={
                    "emaPeriod": [Decimal("10"), Decimal("20"), Decimal("30")],
                    "stopLossPct": [
                        Decimal("1.0"),
                        Decimal("2.0"),
                        Decimal("3.0"),
                    ],
                }
            ),
        )
        assert req.backtest_id == backtest_id
        assert len(req.params.param_grid) == 2


class TestParamStabilityParamsStrictDecimalInput:
    """Sprint 53 BL-226 — StrictDecimalInput Request-boundary canonicalization.

    FE `isFiniteDecimalString` regex `^-?\\d+(\\.\\d+)?$` 와 BE Pydantic Decimal
    grammar 정합. `1e-3`, `.5`, `+1`, `Decimal("NaN")`, `Decimal("1E+5")` reject.
    """

    def test_scientific_notation_string_rejected(self) -> None:
        """param_grid value `"1e-3"` reject (FE regex 와 mirror)."""
        with pytest.raises(ValueError):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": ["1e-3"],  # type: ignore[list-item]
                    "stopLossPct": [Decimal("1.0")],
                }
            )

    def test_leading_dot_string_rejected(self) -> None:
        """param_grid value `".5"` reject."""
        with pytest.raises(ValueError):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": [".5"],  # type: ignore[list-item]
                    "stopLossPct": [Decimal("1.0")],
                }
            )

    def test_plus_prefix_string_rejected(self) -> None:
        """param_grid value `"+1"` reject."""
        with pytest.raises(ValueError):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": ["+1"],  # type: ignore[list-item]
                    "stopLossPct": [Decimal("1.0")],
                }
            )

    def test_nan_decimal_instance_rejected(self) -> None:
        """param_grid value `Decimal("NaN")` reject (canonicalization)."""
        with pytest.raises(ValueError):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": [Decimal("NaN")],
                    "stopLossPct": [Decimal("1.0")],
                }
            )

    def test_large_exponent_decimal_instance_rejected(self) -> None:
        """param_grid value `Decimal("1E+5")` reject (canonicalization)."""
        with pytest.raises(ValueError):
            ParamStabilityParams(
                param_grid={
                    "emaPeriod": [Decimal("1E+5")],
                    "stopLossPct": [Decimal("1.0")],
                }
            )


class TestParamStabilityResultOut:
    """Result serialization — Decimal → str (FE 정합)."""

    def test_result_round_trip(self) -> None:
        """9-cell result 정상 serialization."""
        cells = [
            ParamStabilityCellOut(
                param1_value=str(p1),
                param2_value=str(p2),
                sharpe="1.23",
                total_return="0.15",
                max_drawdown="-0.05",
                num_trades=10,
                is_degenerate=False,
            )
            for p1 in [10, 20, 30]
            for p2 in [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")]
        ]
        result = ParamStabilityResultOut(
            param1_name="emaPeriod",
            param2_name="stopLossPct",
            param1_values=["10", "20", "30"],
            param2_values=["1.0", "2.0", "3.0"],
            cells=cells,
        )
        assert len(result.cells) == 9
        assert result.cells[0].param1_value == "10"
        assert result.cells[0].param2_value == "1.0"

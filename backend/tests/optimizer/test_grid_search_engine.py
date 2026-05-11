# Sprint 54 — Optimizer Grid Search engine unit tests (pure functions, no DB).

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from src.optimizer.engine.grid_search import (
    GridSearchCell,
    _expand_decimal_field,
    _expand_integer_field,
    _expand_param_space,
    _pick_best_cell_index,
)
from src.optimizer.exceptions import (
    OptimizationObjectiveUnsupportedError,
    OptimizationParameterUnsupportedError,
)
from src.optimizer.schemas import (
    DecimalField,
    IntegerField,
    ParamSpace,
)


def _build_param_space(
    parameters: dict[str, Any],
    *,
    objective_metric: str = "sharpe_ratio",
    direction: str = "maximize",
    max_evaluations: int = 9,
) -> ParamSpace:
    return ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": objective_metric,
            "direction": direction,
            "max_evaluations": max_evaluations,
            "parameters": parameters,
        }
    )


class TestExpandIntegerField:
    def test_expand_int_inclusive_endpoints(self) -> None:
        """min=10, max=30, step=5 → [10, 15, 20, 25, 30]."""
        field = IntegerField(min=10, max=30, step=5)
        out = _expand_integer_field(field)
        assert out == [Decimal(10), Decimal(15), Decimal(20), Decimal(25), Decimal(30)]

    def test_expand_int_step_1_default(self) -> None:
        field = IntegerField(min=1, max=3)
        out = _expand_integer_field(field)
        assert out == [Decimal(1), Decimal(2), Decimal(3)]

    def test_expand_int_min_equals_max(self) -> None:
        field = IntegerField(min=5, max=5, step=1)
        out = _expand_integer_field(field)
        assert out == [Decimal(5)]


class TestExpandDecimalField:
    def test_expand_decimal_inclusive_endpoints(self) -> None:
        field = DecimalField(min=Decimal("0.5"), max=Decimal("2.0"), step=Decimal("0.5"))
        out = _expand_decimal_field(field)
        assert out == [
            Decimal("0.5"), Decimal("1.0"), Decimal("1.5"), Decimal("2.0"),
        ]

    def test_expand_decimal_single_value(self) -> None:
        field = DecimalField(min=Decimal("1"), max=Decimal("1"), step=Decimal("0.5"))
        out = _expand_decimal_field(field)
        assert out == [Decimal("1")]


class TestExpandParamSpace:
    def test_two_integer_fields(self) -> None:
        space = _build_param_space(
            {
                "emaPeriod": {"kind": "integer", "min": 10, "max": 20, "step": 5},
                "rsiPeriod": {"kind": "integer", "min": 7, "max": 14, "step": 7},
            }
        )
        grid = _expand_param_space(space)
        assert grid == {
            "emaPeriod": [Decimal(10), Decimal(15), Decimal(20)],
            "rsiPeriod": [Decimal(7), Decimal(14)],
        }

    def test_mixed_int_and_decimal(self) -> None:
        space = _build_param_space(
            {
                "ema": {"kind": "integer", "min": 10, "max": 20, "step": 10},
                "stop": {"kind": "decimal", "min": "1.0", "max": "2.0", "step": "0.5"},
            }
        )
        grid = _expand_param_space(space)
        assert grid["ema"] == [Decimal(10), Decimal(20)]
        assert grid["stop"] == [Decimal("1.0"), Decimal("1.5"), Decimal("2.0")]

    def test_categorical_field_rejected(self) -> None:
        """Sprint 54 MVP — categorical 은 ADR-013 Sprint 55+."""
        space = _build_param_space(
            {
                "exit_mode": {"kind": "categorical", "values": ["a", "b", "c"]},
            }
        )
        with pytest.raises(OptimizationParameterUnsupportedError) as exc_info:
            _expand_param_space(space)
        assert exc_info.value.var_name == "exit_mode"
        assert exc_info.value.kind == "categorical"


class TestPickBestCellIndex:
    def _make_cell(
        self,
        *,
        objective_value: Decimal | None,
        is_degenerate: bool = False,
    ) -> GridSearchCell:
        return GridSearchCell(
            param_values={"x": Decimal("1")},
            sharpe=objective_value,
            total_return=Decimal("0"),
            max_drawdown=Decimal("0"),
            num_trades=10,
            is_degenerate=is_degenerate,
            objective_value=objective_value,
        )

    def test_maximize_picks_highest(self) -> None:
        cells = (
            self._make_cell(objective_value=Decimal("0.5")),
            self._make_cell(objective_value=Decimal("1.8")),  # best
            self._make_cell(objective_value=Decimal("1.2")),
        )
        assert _pick_best_cell_index(cells, direction="maximize") == 1

    def test_minimize_picks_lowest(self) -> None:
        cells = (
            self._make_cell(objective_value=Decimal("0.5")),
            self._make_cell(objective_value=Decimal("0.2")),  # best minimize
            self._make_cell(objective_value=Decimal("1.2")),
        )
        assert _pick_best_cell_index(cells, direction="minimize") == 1

    def test_skips_degenerate_cells(self) -> None:
        cells = (
            self._make_cell(objective_value=None, is_degenerate=True),
            self._make_cell(objective_value=Decimal("1.0")),  # only candidate
            self._make_cell(objective_value=None, is_degenerate=True),
        )
        assert _pick_best_cell_index(cells, direction="maximize") == 1

    def test_all_degenerate_returns_none(self) -> None:
        cells = (
            self._make_cell(objective_value=None, is_degenerate=True),
            self._make_cell(objective_value=None, is_degenerate=True),
        )
        assert _pick_best_cell_index(cells, direction="maximize") is None


class TestObjectiveMetricWhitelist:
    """objective_metric 화이트리스트 — schemas 는 free str 받지만 executor 가 reject."""

    def test_unsupported_objective_metric_rejected_at_run_time(self) -> None:
        # ParamSpace schemas 가 objective_metric free str 받음 — executor 에서 reject 필수.
        space = _build_param_space(
            {"ema": {"kind": "integer", "min": 10, "max": 10, "step": 1}},
            objective_metric="profit_factor",  # 화이트리스트 밖
        )
        # 호출 자체는 ParamSpace 검증 통과. executor entry 가 reject.
        from src.optimizer.engine.grid_search import run_grid_search

        with pytest.raises(OptimizationObjectiveUnsupportedError):
            # ohlcv 등 인수 fake — entry 에서 reject 되므로 도달 안 함.
            run_grid_search(
                "// fake pine",
                None,  # type: ignore[arg-type]
                param_space=space,
            )


def test_grid_search_result_serialization_roundtrip() -> None:
    """serializers to_jsonb → from_jsonb round-trip 보존."""
    from src.optimizer.engine import GridSearchCell, GridSearchResult
    from src.optimizer.serializers import (
        grid_search_result_from_jsonb,
        grid_search_result_to_jsonb,
    )

    result = GridSearchResult(
        param_names=("ema", "stop"),
        param_values={
            "ema": (Decimal("10"), Decimal("20")),
            "stop": (Decimal("0.5"), Decimal("1.0")),
        },
        cells=(
            GridSearchCell(
                param_values={"ema": Decimal("10"), "stop": Decimal("0.5")},
                sharpe=Decimal("1.5"),
                total_return=Decimal("0.30"),
                max_drawdown=Decimal("-0.05"),
                num_trades=15,
                is_degenerate=False,
                objective_value=Decimal("1.5"),
            ),
            GridSearchCell(
                param_values={"ema": Decimal("20"), "stop": Decimal("1.0")},
                sharpe=None,
                total_return=Decimal("0"),
                max_drawdown=Decimal("0"),
                num_trades=0,
                is_degenerate=True,
                objective_value=None,
            ),
        ),
        objective_metric="sharpe_ratio",
        direction="maximize",
        best_cell_index=0,
    )
    jsonb = grid_search_result_to_jsonb(result)
    restored = grid_search_result_from_jsonb(jsonb)

    assert restored.param_names == result.param_names
    assert restored.best_cell_index == 0
    assert restored.cells[0].sharpe == Decimal("1.5")
    assert restored.cells[1].sharpe is None
    assert restored.cells[1].is_degenerate is True
    assert restored.objective_metric == "sharpe_ratio"
    assert restored.direction == "maximize"


def test_optimization_execution_error_public_internal_split() -> None:
    """BL-230 — public 메시지와 internal 메시지 분리 유지."""
    from src.optimizer.exceptions import (
        MAX_ERROR_MESSAGE_LEN,
        OptimizationExecutionError,
        truncate_error_message,
    )

    err = OptimizationExecutionError(
        message_public="Backtest execution failed for one of the cells.",
        message_internal="cell=(...) traceback line 42 ValueError: <very detailed>",
    )
    assert err.message_public != err.message_internal
    assert err.detail == err.message_public  # FE 에 노출되는 detail = public.

    # truncate helper — 상한 초과 시 marker.
    long_msg = "x" * (MAX_ERROR_MESSAGE_LEN + 100)
    truncated = truncate_error_message(long_msg)
    assert len(truncated) <= MAX_ERROR_MESSAGE_LEN
    assert truncated.endswith("…[truncated]")

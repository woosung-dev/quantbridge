# Optimizer schemas 검증 (Sprint 53 — discriminated union grammar, codex P1 fix).

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.optimizer.schemas import (
    CategoricalField,
    CreateOptimizationRunRequest,
    DecimalField,
    IntegerField,
    OptimizationKindOut,
    ParamSpace,
)


def test_create_request_validates_required_fields() -> None:
    """backtest_id + kind + param_space 누락 시 ValidationError."""
    with pytest.raises(ValidationError):
        CreateOptimizationRunRequest.model_validate({})  # type: ignore[arg-type]

    # minimal valid request
    req = CreateOptimizationRunRequest.model_validate(
        {
            "backtest_id": "00000000-0000-0000-0000-000000000001",
            "kind": "grid_search",
            "param_space": {
                "schema_version": 1,
                "objective_metric": "sharpe_ratio",
                "direction": "maximize",
                "max_evaluations": 9,
                "parameters": {},
            },
        }
    )
    assert req.kind == OptimizationKindOut.GRID_SEARCH


def test_param_space_discriminated_union_integer_kind() -> None:
    """integer field — kind=integer + min/max/step 정의."""
    space = ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 9,
            "parameters": {
                "emaPeriod": {"kind": "integer", "min": 10, "max": 30, "step": 5},
            },
        }
    )
    field = space.parameters["emaPeriod"]
    assert isinstance(field, IntegerField)
    assert field.min == 10
    assert field.max == 30
    assert field.step == 5


def test_param_space_discriminated_union_decimal_kind() -> None:
    """decimal field — kind=decimal + min/max/step Decimal."""
    space = ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": "total_return",
            "direction": "maximize",
            "max_evaluations": 9,
            "parameters": {
                "stopLossPct": {"kind": "decimal", "min": "0.5", "max": "2.0", "step": "0.5"},
            },
        }
    )
    field = space.parameters["stopLossPct"]
    assert isinstance(field, DecimalField)
    assert field.min == Decimal("0.5")
    assert field.max == Decimal("2.0")
    assert field.step == Decimal("0.5")


def test_param_space_discriminated_union_categorical_kind() -> None:
    """categorical field — kind=categorical + values list."""
    space = ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 3,
            "parameters": {
                "exitMode": {"kind": "categorical", "values": ["trailing", "fixed", "atr"]},
            },
        }
    )
    field = space.parameters["exitMode"]
    assert isinstance(field, CategoricalField)
    assert field.values == ["trailing", "fixed", "atr"]


def test_param_space_unknown_kind_reject() -> None:
    """discriminator 'kind' 미상 값 → ValidationError (Sprint 54 bayesian/genetic 등재 전 reject)."""
    with pytest.raises(ValidationError):
        ParamSpace.model_validate(
            {
                "schema_version": 1,
                "objective_metric": "sharpe_ratio",
                "direction": "maximize",
                "max_evaluations": 9,
                "parameters": {
                    "unknown_field": {"kind": "log_uniform", "min": 0.0, "max": 1.0},
                },
            }
        )


def test_param_space_schema_version_locked_to_1() -> None:
    """schema_version Literal[1] — 2 등 reject (Sprint 54 grammar 확장 시 명시 분기)."""
    with pytest.raises(ValidationError):
        ParamSpace.model_validate(
            {
                "schema_version": 2,
                "objective_metric": "sharpe_ratio",
                "direction": "maximize",
                "max_evaluations": 9,
                "parameters": {},
            }
        )


def test_param_space_direction_enum_locked() -> None:
    """direction = maximize/minimize 만 허용."""
    with pytest.raises(ValidationError):
        ParamSpace.model_validate(
            {
                "schema_version": 1,
                "objective_metric": "sharpe_ratio",
                "direction": "best",  # invalid
                "max_evaluations": 9,
                "parameters": {},
            }
        )


# === codex G.4 P1#2 / P1#3 invariant tests ===


def test_decimal_field_strict_decimal_input_rejects_exponent_string() -> None:
    """DecimalField.min `"1e-3"` reject (BL-226 stress_test parity)."""
    with pytest.raises(ValidationError):
        DecimalField.model_validate({"kind": "decimal", "min": "1e-3", "max": "2", "step": "1"})


def test_decimal_field_strict_decimal_input_rejects_nan_decimal() -> None:
    """DecimalField.min `Decimal("NaN")` reject."""
    with pytest.raises(ValidationError):
        DecimalField.model_validate(
            {"kind": "decimal", "min": Decimal("NaN"), "max": Decimal("2"), "step": Decimal("1")}
        )


def test_integer_field_step_zero_rejected() -> None:
    """codex G.4 P1#3 — IntegerField step=0 reject (Sprint 54 무한 루프 차단)."""
    with pytest.raises(ValidationError):
        IntegerField.model_validate({"kind": "integer", "min": 1, "max": 10, "step": 0})


def test_integer_field_negative_step_rejected() -> None:
    with pytest.raises(ValidationError):
        IntegerField.model_validate({"kind": "integer", "min": 1, "max": 10, "step": -1})


def test_integer_field_min_greater_than_max_rejected() -> None:
    with pytest.raises(ValidationError):
        IntegerField.model_validate({"kind": "integer", "min": 10, "max": 1, "step": 1})


def test_decimal_field_zero_step_rejected() -> None:
    """DecimalField step=0 reject."""
    with pytest.raises(ValidationError):
        DecimalField.model_validate({"kind": "decimal", "min": "1", "max": "10", "step": "0"})


def test_decimal_field_min_greater_than_max_rejected() -> None:
    with pytest.raises(ValidationError):
        DecimalField.model_validate({"kind": "decimal", "min": "10", "max": "1", "step": "1"})

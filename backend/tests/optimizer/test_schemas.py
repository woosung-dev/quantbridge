# Optimizer schemas 검증 (Sprint 53 — discriminated union grammar, codex P1 fix).

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.optimizer.schemas import (
    BayesianHyperparamsField,
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


def test_param_space_schema_version_3_rejected() -> None:
    """schema_version Literal[1, 2] — 3 등 reject (Sprint 55 = 1/2 활성, Sprint 56+ = grammar amendment)."""
    with pytest.raises(ValidationError):
        ParamSpace.model_validate(
            {
                "schema_version": 3,
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


# === Sprint 55 — schema_version=2 + BayesianHyperparamsField (ADR-013 §6 #1, #2, #7) ===


def test_param_space_schema_version_2_accepts_bayesian_field() -> None:
    """ParamSpace schema_version=2 + BayesianHyperparamsField + bayesian_acquisition 정상 통과."""
    space = ParamSpace.model_validate(
        {
            "schema_version": 2,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 30,
            "parameters": {
                "emaPeriod": {
                    "kind": "bayesian",
                    "min": "5",
                    "max": "30",
                    "prior": "uniform",
                    "log_scale": False,
                },
            },
            "bayesian_n_initial_random": 10,
            "bayesian_acquisition": "EI",
        }
    )
    field = space.parameters["emaPeriod"]
    assert isinstance(field, BayesianHyperparamsField)
    assert field.min == Decimal("5")
    assert field.max == Decimal("30")
    assert field.prior == "uniform"
    assert space.bayesian_n_initial_random == 10
    assert space.bayesian_acquisition == "EI"


def test_bayesian_field_log_scale_requires_positive_min() -> None:
    """ADR-013 §2.5 — log_scale=True 또는 prior='log_uniform' 시 min > 0 강제."""
    with pytest.raises(ValidationError, match="min > 0"):
        BayesianHyperparamsField.model_validate(
            {
                "kind": "bayesian",
                "min": "0",
                "max": "10",
                "prior": "uniform",
                "log_scale": True,
            }
        )
    with pytest.raises(ValidationError, match="min > 0"):
        BayesianHyperparamsField.model_validate(
            {
                "kind": "bayesian",
                "min": "-1",
                "max": "10",
                "prior": "log_uniform",
                "log_scale": False,
            }
        )


def test_bayesian_field_min_max_invariant() -> None:
    """BayesianHyperparamsField.min < max 강제 (Bayesian 은 grid step X → strict less than)."""
    with pytest.raises(ValidationError, match="min must be < max"):
        BayesianHyperparamsField.model_validate(
            {"kind": "bayesian", "min": "10", "max": "10", "prior": "uniform", "log_scale": False}
        )
    with pytest.raises(ValidationError, match="min must be < max"):
        BayesianHyperparamsField.model_validate(
            {"kind": "bayesian", "min": "20", "max": "5", "prior": "uniform", "log_scale": False}
        )


def test_param_space_schema_v1_rejects_bayesian_optional_fields() -> None:
    """schema_version=1 시 5 v2-only 필드 (bayesian_*/population_*/n_generations/mutation_rate) 모두 reject."""
    with pytest.raises(ValidationError, match="schema_version=1 forbids v2-only fields"):
        ParamSpace.model_validate(
            {
                "schema_version": 1,
                "objective_metric": "sharpe_ratio",
                "direction": "maximize",
                "max_evaluations": 9,
                "parameters": {
                    "emaPeriod": {"kind": "integer", "min": 10, "max": 30, "step": 5},
                },
                "bayesian_acquisition": "EI",
            }
        )
    with pytest.raises(ValidationError, match="schema_version=1 forbids BayesianHyperparamsField"):
        ParamSpace.model_validate(
            {
                "schema_version": 1,
                "objective_metric": "sharpe_ratio",
                "direction": "maximize",
                "max_evaluations": 9,
                "parameters": {
                    "emaPeriod": {
                        "kind": "bayesian",
                        "min": "5",
                        "max": "30",
                        "prior": "uniform",
                        "log_scale": False,
                    },
                },
            }
        )


def test_param_space_v1_round_trip_unchanged_grid_search() -> None:
    """회귀 차단 — schema_version=1 + IntegerField + 5 v2-only 필드 모두 None 으로 round-trip."""
    original = {
        "schema_version": 1,
        "objective_metric": "sharpe_ratio",
        "direction": "maximize",
        "max_evaluations": 9,
        "parameters": {
            "emaPeriod": {"kind": "integer", "min": 10, "max": 30, "step": 5},
            "stopLossPct": {"kind": "decimal", "min": "0.5", "max": "2.0", "step": "0.5"},
        },
    }
    space = ParamSpace.model_validate(original)
    assert space.schema_version == 1
    assert space.bayesian_n_initial_random is None
    assert space.bayesian_acquisition is None
    assert space.population_size is None
    assert space.n_generations is None
    assert space.mutation_rate is None
    # round-trip dump → 원본 5 v2-only 필드는 default None 유지.
    dumped = space.model_dump(mode="json", exclude_none=True)
    assert "bayesian_acquisition" not in dumped
    assert "bayesian_n_initial_random" not in dumped
    assert "population_size" not in dumped
    assert "n_generations" not in dumped
    assert "mutation_rate" not in dumped
    # parameters 보존.
    assert dumped["parameters"]["emaPeriod"]["kind"] == "integer"
    assert dumped["parameters"]["stopLossPct"]["kind"] == "decimal"

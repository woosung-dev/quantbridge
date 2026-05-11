# Optimizer 도메인 Pydantic V2 schemas — Sprint 55 schema_version=2 + Bayesian discriminated union 확장.

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.common.strict_decimal_input import StrictDecimalInput


class OptimizationKindOut(StrEnum):
    """FE mirror — Sprint 56 = GENETIC 추가 (Sprint 55 Bayesian 패턴 mirror, BL-233)."""

    GRID_SEARCH = "grid_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"


class OptimizationStatusOut(StrEnum):
    """FE mirror — StressTestStatus grammar 재사용."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IntegerField(BaseModel):
    """정수 탐색 field — pine input.int sweep용."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["integer"] = "integer"
    min: int
    max: int
    step: int = 1

    @model_validator(mode="after")
    def _validate_invariants(self) -> IntegerField:
        # codex G.4 P1#3 — schema lock 단계 invariant 강제.
        # Sprint 54 grid expansion 안 step=0 시 무한 루프 / min>max 시 빈 cardinality 차단.
        if self.step <= 0:
            raise ValueError(f"IntegerField.step must be positive (got {self.step})")
        if self.min > self.max:
            raise ValueError(
                f"IntegerField.min must be <= max (got min={self.min}, max={self.max})"
            )
        return self


class DecimalField(BaseModel):
    """Decimal 탐색 field — pine input.float sweep용.

    codex G.4 P1#2 fix: StrictDecimalInput 사용 — stress_test BL-226 와 일관성.
    `"1e-3"`, `Decimal("NaN")`, `"9" * 400` overflow 모두 Request-boundary 에서 reject.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["decimal"] = "decimal"
    min: StrictDecimalInput
    max: StrictDecimalInput
    step: StrictDecimalInput

    @model_validator(mode="after")
    def _validate_invariants(self) -> DecimalField:
        # codex G.4 P1#3 — schema lock 단계 invariant 강제.
        if self.step <= Decimal("0"):
            raise ValueError(f"DecimalField.step must be positive (got {self.step})")
        if self.min > self.max:
            raise ValueError(
                f"DecimalField.min must be <= max (got min={self.min}, max={self.max})"
            )
        return self


class CategoricalField(BaseModel):
    """범주형 탐색 field — pine input.string / 사용자 정의 선택지."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["categorical"] = "categorical"
    values: list[str] = Field(min_length=1)


class BayesianHyperparamsField(BaseModel):
    """Bayesian 탐색 field — Sprint 55 ADR-013 §2.1 등재.

    skopt Optimizer.ask/tell loop 의 sampling space 1개 변수에 매핑된다.
    `prior=normal` 은 skopt 미지원 — Sprint 55 = 자체 sampler wrapper (engine/bayesian.py).
    `log_scale=True` 또는 `prior="log_uniform"` 시 min > 0 강제 (log10 정의역).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["bayesian"] = "bayesian"
    min: StrictDecimalInput
    max: StrictDecimalInput
    prior: Literal["uniform", "log_uniform", "normal"] = "uniform"
    log_scale: bool = False

    @model_validator(mode="after")
    def _validate_invariants(self) -> BayesianHyperparamsField:
        if self.min >= self.max:
            raise ValueError(
                f"BayesianHyperparamsField.min must be < max (got min={self.min}, max={self.max})"
            )
        if (self.log_scale or self.prior == "log_uniform") and self.min <= Decimal("0"):
            raise ValueError(
                "BayesianHyperparamsField log_scale=True or prior='log_uniform' requires min > 0 "
                f"(ADR-013 §2.5; got min={self.min})"
            )
        return self


# Discriminated union — Sprint 55 BayesianHyperparamsField 추가 (4-variant).
ParamSpaceField = Annotated[
    IntegerField | DecimalField | CategoricalField | BayesianHyperparamsField,
    Field(discriminator="kind"),
]


class ParamSpace(BaseModel):
    """탐색 공간 grammar — Sprint 55 schema_version=2 확장 (Bayesian executor 본격).

    schema_version=1 = Grid Search MVP (BayesianHyperparamsField + 6 optional 필드 reject).
    schema_version=2 = Bayesian + Genetic 동시 활성 (Sprint 56 ADR-013 §7 amendment).
    cross-field validator 가 양쪽 path invariant 강제 (ADR-013 §2.2).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1, 2] = 1
    objective_metric: str  # e.g. "sharpe_ratio" / "total_return" / "max_drawdown"
    direction: Literal["maximize", "minimize"]
    max_evaluations: int = Field(gt=0)
    parameters: dict[str, ParamSpaceField]

    # Sprint 55 = Bayesian 활성 2 필드 (schema_version=2 only).
    bayesian_n_initial_random: int | None = Field(default=None, ge=1, le=50)
    bayesian_acquisition: Literal["EI", "UCB", "PI"] | None = None

    # Sprint 56 = Genetic 4 필드 활성 (ADR-013 §2.1 + §7 amendment, schema_version=2 only).
    # population_size / n_generations / mutation_rate 는 Sprint 55 prereq reservation,
    # crossover_rate 는 Sprint 56 신규 (Bayesian 와 달리 ParamSpace level hyperparam).
    population_size: int | None = Field(default=None, ge=2, le=200)
    n_generations: int | None = Field(default=None, ge=1, le=100)
    mutation_rate: StrictDecimalInput | None = None
    crossover_rate: StrictDecimalInput | None = None

    @model_validator(mode="after")
    def _validate_cross_field(self) -> ParamSpace:
        """schema_version * parameter kind * optional 필드 invariant (ADR-013 §2.2)."""
        v2_only_fields = {
            "bayesian_n_initial_random": self.bayesian_n_initial_random,
            "bayesian_acquisition": self.bayesian_acquisition,
            "population_size": self.population_size,
            "n_generations": self.n_generations,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
        }
        has_bayesian_field = any(
            isinstance(p, BayesianHyperparamsField) for p in self.parameters.values()
        )

        if self.schema_version == 1:
            populated_v2 = [name for name, val in v2_only_fields.items() if val is not None]
            if populated_v2:
                raise ValueError(
                    f"ParamSpace schema_version=1 forbids v2-only fields {sorted(populated_v2)}; "
                    f"set schema_version=2 to enable Bayesian/Genetic."
                )
            if has_bayesian_field:
                raise ValueError(
                    "ParamSpace schema_version=1 forbids BayesianHyperparamsField; "
                    "set schema_version=2 to enable Bayesian executor."
                )

        if has_bayesian_field and self.schema_version != 2:
            raise ValueError(
                "BayesianHyperparamsField requires schema_version=2 (ADR-013 §2.2)."
            )

        # Sprint 56 — Genetic rate 필드 범위 검증 (0 < x <= 1). ADR-013 §7 amendment.
        # population_size / n_generations 은 Field(ge=2, le=200) / Field(ge=1, le=100) 으로
        # Pydantic 이 1차 강제. mutation_rate / crossover_rate 는 StrictDecimalInput 이라
        # 범위 강제 책임을 cross-field validator 가 가진다.
        if self.mutation_rate is not None and not (
            Decimal("0") < self.mutation_rate <= Decimal("1")
        ):
            raise ValueError(
                f"ParamSpace.mutation_rate must be in (0, 1] "
                f"(got {self.mutation_rate}). ADR-013 §7 amendment."
            )
        if self.crossover_rate is not None and not (
            Decimal("0") < self.crossover_rate <= Decimal("1")
        ):
            raise ValueError(
                f"ParamSpace.crossover_rate must be in (0, 1] "
                f"(got {self.crossover_rate}). ADR-013 §7 amendment."
            )

        return self


class CreateOptimizationRunRequest(BaseModel):
    """POST /optimizer/runs request (Sprint 54 본격 endpoint 등록 시 사용)."""

    model_config = ConfigDict(extra="forbid")

    backtest_id: UUID
    kind: OptimizationKindOut
    param_space: ParamSpace


class OptimizationRunResponse(BaseModel):
    """GET /optimizer/runs/{id} response (Sprint 54 본격 endpoint 등록 시 사용).

    Decimal → str 직렬화 (stress_test/schemas.py 패턴 mirror).
    """

    model_config = ConfigDict(extra="forbid", json_encoders={Decimal: str})

    id: UUID
    user_id: UUID
    backtest_id: UUID
    kind: OptimizationKindOut
    status: OptimizationStatusOut
    param_space: ParamSpace
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

# Optimizer 도메인 Pydantic V2 schemas — Sprint 53 discriminated union grammar lock.

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.common.strict_decimal_input import StrictDecimalInput


class OptimizationKindOut(StrEnum):
    """FE mirror — Sprint 54 본격 구현 시 Bayesian / Genetic 추가."""

    GRID_SEARCH = "grid_search"


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


# Discriminated union — codex G.0 P1#4 fix. `dict[str, Any]` lock 미흡 해소.
ParamSpaceField = Annotated[
    IntegerField | DecimalField | CategoricalField,
    Field(discriminator="kind"),
]


class ParamSpace(BaseModel):
    """탐색 공간 grammar — Sprint 54 grid_search / 미래 bayesian/genetic 양쪽 수용 contract.

    schema_version Literal[1] = grammar lock. Sprint 54+ 확장 시 명시 분기 의무.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    objective_metric: str  # e.g. "sharpe_ratio" / "total_return" / "max_drawdown"
    direction: Literal["maximize", "minimize"]
    max_evaluations: int = Field(gt=0)
    parameters: dict[str, ParamSpaceField]


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

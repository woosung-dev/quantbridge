"""stress_test 도메인 Pydantic V2 스키마 — Request/Response DTOs."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_serializer

from src.stress_test.models import StressTestKind, StressTestStatus

# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------


class MonteCarloParams(BaseModel):
    """Monte Carlo bootstrap 파라미터."""

    n_samples: int = Field(default=1000, ge=10, le=10_000)
    seed: int = Field(default=42, ge=0)


class MonteCarloSubmitRequest(BaseModel):
    """POST /stress-tests/monte-carlo body."""

    backtest_id: UUID
    params: MonteCarloParams = Field(default_factory=MonteCarloParams)


class MonteCarloResultOut(BaseModel):
    """MC result JSONB → API.

    `equity_percentiles` 는 `{"5": [...], ...}` 형태의 Decimal str 시계열.
    """

    samples: int
    ci_lower_95: Decimal
    ci_upper_95: Decimal
    median_final_equity: Decimal
    max_drawdown_mean: Decimal
    max_drawdown_p95: Decimal
    equity_percentiles: dict[str, list[Decimal]]

    @field_serializer(
        "ci_lower_95",
        "ci_upper_95",
        "median_final_equity",
        "max_drawdown_mean",
        "max_drawdown_p95",
    )
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)

    @field_serializer("equity_percentiles")
    def _percentiles_to_str(self, v: dict[str, list[Decimal]]) -> dict[str, list[str]]:
        return {k: [str(x) for x in series] for k, series in v.items()}


# ---------------------------------------------------------------------------
# Walk-Forward
# ---------------------------------------------------------------------------


class WalkForwardParams(BaseModel):
    """Walk-Forward 파라미터."""

    train_bars: int = Field(ge=1)
    test_bars: int = Field(ge=1)
    step_bars: int | None = Field(default=None, ge=1)
    max_folds: int = Field(default=20, ge=1, le=100)


class WalkForwardSubmitRequest(BaseModel):
    """POST /stress-tests/walk-forward body."""

    backtest_id: UUID
    params: WalkForwardParams


class WalkForwardFoldOut(BaseModel):
    """1 fold out."""

    fold_index: int
    train_start: AwareDatetime
    train_end: AwareDatetime
    test_start: AwareDatetime
    test_end: AwareDatetime
    in_sample_return: Decimal
    out_of_sample_return: Decimal
    oos_sharpe: Decimal | None
    num_trades_oos: int

    @field_serializer(
        "in_sample_return",
        "out_of_sample_return",
        "oos_sharpe",
    )
    def _decimal_to_str(self, v: Decimal | None) -> str | None:
        return None if v is None else str(v)


class WalkForwardResultOut(BaseModel):
    """WFA result JSONB → API.

    `degradation_ratio` 는 `Decimal("Infinity")` 가 될 수 있으며, 저장/노출 시
    문자열 `"Infinity"` 를 그대로 사용한다. FE 는 `valid_positive_regime=False`
    또는 `degradation_ratio=="Infinity"` 를 "N/A" 로 렌더링해야 한다.
    """

    folds: list[WalkForwardFoldOut]
    aggregate_oos_return: Decimal
    degradation_ratio: str  # Decimal or "Infinity"
    valid_positive_regime: bool
    total_possible_folds: int
    was_truncated: bool

    @field_serializer("aggregate_oos_return")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


# ---------------------------------------------------------------------------
# Common Response
# ---------------------------------------------------------------------------


class StressTestCreatedResponse(BaseModel):
    """POST → 202 Accepted."""

    stress_test_id: UUID
    kind: StressTestKind
    status: StressTestStatus
    created_at: AwareDatetime


class StressTestSummary(BaseModel):
    """목록 항목 — result 미포함."""

    id: UUID
    backtest_id: UUID
    kind: StressTestKind
    status: StressTestStatus
    created_at: AwareDatetime
    completed_at: AwareDatetime | None

    model_config = ConfigDict(from_attributes=True)


class StressTestDetail(BaseModel):
    """GET /:id 상세 — result 포함 (kind 별 구조)."""

    id: UUID
    backtest_id: UUID
    kind: StressTestKind
    status: StressTestStatus
    params: dict[str, object]
    monte_carlo_result: MonteCarloResultOut | None = None
    walk_forward_result: WalkForwardResultOut | None = None
    error: str | None = None
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None


# Literal for router path kind (just for type narrowing).
StressKindLiteral = Literal["monte_carlo", "walk_forward"]

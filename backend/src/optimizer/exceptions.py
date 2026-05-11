# Optimizer 도메인 예외 — Sprint 53 skeleton + Sprint 54 BL-230 execution error 분리.

from __future__ import annotations

from typing import Final
from uuid import UUID

from fastapi import status

from src.common.exceptions import AppException, NotFoundError, ValidationError

# Sprint 54 BL-230: optimization_runs.error_message Text 컬럼 truncation 상한.
# public/internal 양쪽 동일 상한 적용. DB row size 예측 가능성 + log spam 방어.
MAX_ERROR_MESSAGE_LEN: Final[int] = 2000


def truncate_error_message(msg: str, *, limit: int = MAX_ERROR_MESSAGE_LEN) -> str:
    """길이 상한 적용. 초과 시 명시적 marker 부착 (silent truncate 금지)."""
    if len(msg) <= limit:
        return msg
    suffix = " …[truncated]"
    head = max(0, limit - len(suffix))
    return msg[:head] + suffix


class OptimizationError(AppException):
    """Optimizer 도메인 base 예외 — codex G.4 P2#2 fix: AppException 계층 의무.

    FastAPI 표준 핸들러 + FE error code contract 정합 유지.
    """


class OptimizationNotFoundError(NotFoundError):
    """OptimizationRun ID 조회 실패 — 404 + machine-readable code."""

    code = "OPTIMIZATION_NOT_FOUND"

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__(f"Optimization run not found: {run_id}")


class OptimizationKindUnsupportedError(ValidationError):
    """미지원 Optimizer 알고리즘 (Sprint 55 = grid_search + bayesian) — 422 + machine-readable code.

    Sprint 56+ = GENETIC executor 활성 시 본 메시지 갱신 의무 (BL-233).
    """

    code = "OPTIMIZATION_KIND_UNSUPPORTED"

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(
            f"Optimization kind {kind!r} not supported. "
            "Sprint 55 supports: {grid_search, bayesian}. "
            "genetic = Sprint 56+ (BL-233)."
        )


class OptimizationParameterUnsupportedError(ValidationError):
    """ParamSpaceField.kind = categorical 등 Sprint 54 MVP 미지원 field — 422.

    Sprint 54 Grid Search MVP = integer + decimal field 만 grid expansion. categorical
    은 Bayesian/Genetic 진입 후 활성화 (ADR-013 reservation).
    """

    code = "OPTIMIZATION_PARAMETER_UNSUPPORTED"

    def __init__(self, var_name: str, kind: str) -> None:
        self.var_name = var_name
        self.kind = kind
        super().__init__(
            f"Optimization parameter {var_name!r} has kind={kind!r}. "
            f"Sprint 54 Grid Search MVP supports only kind ∈ {{integer, decimal}}. "
            f"categorical extension tracked under ADR-013 (Sprint 55+)."
        )


class OptimizationObjectiveUnsupportedError(ValidationError):
    """objective_metric 화이트리스트 밖 — 422.

    Sprint 54 MVP whitelist = {sharpe_ratio, total_return, max_drawdown}.
    BacktestMetrics 다른 24 지표는 Sprint 55+ 확장.
    """

    code = "OPTIMIZATION_OBJECTIVE_UNSUPPORTED"

    def __init__(self, objective_metric: str) -> None:
        self.objective_metric = objective_metric
        super().__init__(
            f"Optimization objective_metric {objective_metric!r} not supported. "
            f"Sprint 54 MVP = {{sharpe_ratio, total_return, max_drawdown}}."
        )


class OptimizationTaskDispatchError(OptimizationError):
    """Celery task enqueue 실패 — 503. StressTest 패턴 mirror."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "OPTIMIZATION_TASK_DISPATCH_FAILED"
    detail = "Failed to dispatch optimization task"


class BacktestNotCompletedForOptimization(OptimizationError):
    """참조된 Backtest 가 COMPLETED 가 아님 — 409. StressTest 패턴 mirror."""

    status_code = status.HTTP_409_CONFLICT
    code = "BACKTEST_NOT_COMPLETED_FOR_OPTIMIZATION"
    detail = "Referenced backtest is not in COMPLETED state"


class OptimizationExecutionError(OptimizationError):
    """Sprint 54 BL-230 — Optimizer executor 실행 실패.

    public/internal 메시지 분리:
        - message_public: FE/API 응답에 노출 (사용자가 이해할 수 있는 단순 문장).
        - message_internal: log + DB row.error_message 저장용 (stack trace 등 포함 가능).

    DB row.error_message 는 ``message_internal`` 을 ``truncate_error_message`` 로
    상한 적용 후 저장 (Service 책임).
    """

    status_code = 500
    code = "OPTIMIZATION_EXECUTION_FAILED"

    def __init__(self, *, message_public: str, message_internal: str | None = None) -> None:
        self.message_public = message_public
        self.message_internal = message_internal or message_public
        super().__init__(message_public)

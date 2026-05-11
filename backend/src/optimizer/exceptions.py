# Optimizer 도메인 예외 — Sprint 53 skeleton (Sprint 54 service 추가 시 본격 raise).

from __future__ import annotations

from uuid import UUID

from src.common.exceptions import AppException, NotFoundError, ValidationError


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
    """미지원 Optimizer 알고리즘 (Sprint 54 = grid_search 만) — 422 + machine-readable code."""

    code = "OPTIMIZATION_KIND_UNSUPPORTED"

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(
            f"Optimization kind {kind!r} not supported. "
            "Sprint 54 MVP = grid_search only."
        )

# Optimizer 도메인 예외 검증 (Sprint 53 skeleton).

from __future__ import annotations

from uuid import uuid4

from src.optimizer.exceptions import (
    OptimizationKindUnsupportedError,
    OptimizationNotFoundError,
)


def test_optimization_not_found_error_carries_id() -> None:
    """ID 가 메시지 + attribute 모두 표시."""
    run_id = uuid4()
    err = OptimizationNotFoundError(run_id)
    assert err.run_id == run_id
    assert str(run_id) in str(err)


def test_optimization_kind_unsupported_error_message() -> None:
    """unsupported kind 명시 메시지 (Sprint 54 = grid_search 만 구현)."""
    err = OptimizationKindUnsupportedError("bayesian")
    assert err.kind == "bayesian"
    assert "bayesian" in str(err)

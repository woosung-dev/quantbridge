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


def test_optimization_kind_unsupported_error_message_lists_supported() -> None:
    """Sprint 55 = grid_search + bayesian. 메시지 안 supported list 노출 의무."""
    err = OptimizationKindUnsupportedError("genetic")
    assert err.kind == "genetic"
    msg = str(err)
    assert "grid_search" in msg
    assert "bayesian" in msg


def test_optimization_kind_unsupported_error_genetic_message() -> None:
    """Sprint 56+ Genetic 활성 path 명시 (BL-233)."""
    err = OptimizationKindUnsupportedError("genetic")
    msg = str(err)
    assert "Sprint 56+" in msg
    assert "BL-233" in msg


def test_optimization_kind_out_bayesian_active() -> None:
    """OptimizationKindOut.BAYESIAN 가 enum 안 활성 (Sprint 55 schemas Slice 1)."""
    from src.optimizer.schemas import OptimizationKindOut

    assert OptimizationKindOut.BAYESIAN.value == "bayesian"
    assert "bayesian" in [k.value for k in OptimizationKindOut]

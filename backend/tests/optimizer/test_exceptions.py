# Optimizer 도메인 예외 검증 (Sprint 53 skeleton).

from __future__ import annotations

from uuid import uuid4

from src.optimizer.exceptions import (
    OptimizationKindUnsupportedError,
    OptimizationNotFoundError,
)
from src.optimizer.models import OptimizationKind


def test_optimization_not_found_error_carries_id() -> None:
    """ID 가 메시지 + attribute 모두 표시."""
    run_id = uuid4()
    err = OptimizationNotFoundError(run_id)
    assert err.run_id == run_id
    assert str(run_id) in str(err)


def test_optimization_kind_unsupported_error_message_lists_supported() -> None:
    """지원 목록은 사용자에게 노출된다."""
    err = OptimizationKindUnsupportedError("unsupported")
    assert err.kind == "unsupported"
    msg = str(err)
    assert "grid_search" in msg
    assert "bayesian" in msg
    assert "genetic" in msg


def test_optimization_kind_unsupported_error_derives_all_enum_values() -> None:
    """새 kind 추가 시 메시지 목록도 enum 순회로 함께 갱신된다."""
    err = OptimizationKindUnsupportedError("unsupported")
    msg = str(err)
    assert all(kind.value in msg for kind in OptimizationKind)
    assert "Sprint" not in msg


def test_optimization_kind_out_bayesian_active() -> None:
    """OptimizationKindOut.BAYESIAN 가 enum 안 활성 (Sprint 55 schemas Slice 1)."""
    from src.optimizer.schemas import OptimizationKindOut

    assert OptimizationKindOut.BAYESIAN.value == "bayesian"
    assert "bayesian" in [k.value for k in OptimizationKindOut]

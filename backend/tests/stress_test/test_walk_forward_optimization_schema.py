# WFO submit 스키마 — optimizer_param_space/kind 모드 (best_params 와 상호배타) 검증.
from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from src.stress_test.schemas import WalkForwardParams


def _ps() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "objective_metric": "sharpe_ratio",
        "direction": "maximize",
        "max_evaluations": 9,
        "parameters": {"emaPeriod": {"kind": "integer", "min": 5, "max": 10, "step": 5}},
    }


def test_plain_params_ok() -> None:
    p = WalkForwardParams(train_bars=100, test_bars=50)
    assert p.optimizer_param_space is None
    assert p.optimizer_kind is None
    assert p.best_params is None


def test_best_params_only_ok() -> None:
    p = WalkForwardParams(train_bars=100, test_bars=50, best_params={"emaPeriod": Decimal("7")})
    assert p.best_params == {"emaPeriod": Decimal("7")}


def test_optimizer_spec_ok() -> None:
    p = WalkForwardParams(
        train_bars=100,
        test_bars=50,
        optimizer_param_space=_ps(),  # type: ignore[arg-type]
        optimizer_kind="grid_search",  # type: ignore[arg-type]
    )
    assert p.optimizer_param_space is not None
    assert p.optimizer_kind == "grid_search"


def test_param_space_without_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        WalkForwardParams(
            train_bars=100, test_bars=50, optimizer_param_space=_ps()  # type: ignore[arg-type]
        )


def test_kind_without_param_space_rejected() -> None:
    with pytest.raises(ValidationError):
        WalkForwardParams(
            train_bars=100, test_bars=50, optimizer_kind="grid_search"  # type: ignore[arg-type]
        )


def test_best_params_and_optimizer_spec_mutually_exclusive() -> None:
    with pytest.raises(ValidationError):
        WalkForwardParams(
            train_bars=100,
            test_bars=50,
            best_params={"emaPeriod": Decimal("7")},
            optimizer_param_space=_ps(),  # type: ignore[arg-type]
            optimizer_kind="grid_search",  # type: ignore[arg-type]
        )


def test_bayesian_kind_requires_schema_version_2() -> None:
    """LOW-2(Evaluator gate 1) — bayesian/genetic 은 schema_version=2 필수.
    schema_version=1 param_space 와 결합 시 worker-time FAILED 대신 submit-time reject (fail-fast).
    """
    with pytest.raises(ValidationError):
        WalkForwardParams(
            train_bars=100,
            test_bars=50,
            optimizer_param_space=_ps(),  # schema_version=1
            optimizer_kind="bayesian",  # type: ignore[arg-type]
        )


def test_grid_search_allows_schema_version_1() -> None:
    p = WalkForwardParams(
        train_bars=100,
        test_bars=50,
        optimizer_param_space=_ps(),  # schema_version=1
        optimizer_kind="grid_search",  # type: ignore[arg-type]
    )
    assert p.optimizer_param_space is not None

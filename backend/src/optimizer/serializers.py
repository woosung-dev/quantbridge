"""Optimizer JSONB 직렬화 helpers — GridSearchResult / BayesianSearchResult ↔ JSONB dict.

Decimal → str, None 보존, row-major iterations / cells 보존. stress_test/serializers.py mirror.

Sprint 55 = BayesianSearchResult 추가. top-level ``kind`` 필드 echo (FE
z.discriminatedUnion("kind") 의무) + ``best_iteration_idx`` 명시 (Sprint 50/51/52
retro-incorrect 패턴 차단).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.optimizer.engine import (
    BayesianIteration,
    BayesianSearchResult,
    GridSearchCell,
    GridSearchResult,
)


def grid_search_result_to_jsonb(r: GridSearchResult) -> dict[str, Any]:
    """GridSearchResult → JSONB dict. Decimal → str, cells row-major flatten.

    Sprint 55 = top-level ``kind: "grid_search"`` echo (FE discriminated union 의무).
    """
    return {
        "schema_version": 1,
        "kind": "grid_search",
        "param_names": list(r.param_names),
        "param_values": {
            k: [str(v) for v in vs] for k, vs in r.param_values.items()
        },
        "cells": [
            {
                "param_values": {k: str(v) for k, v in c.param_values.items()},
                "sharpe": None if c.sharpe is None else str(c.sharpe),
                "total_return": str(c.total_return),
                "max_drawdown": str(c.max_drawdown),
                "num_trades": c.num_trades,
                "is_degenerate": c.is_degenerate,
                "objective_value": (
                    None if c.objective_value is None else str(c.objective_value)
                ),
            }
            for c in r.cells
        ],
        "objective_metric": r.objective_metric,
        "direction": r.direction,
        "best_cell_index": r.best_cell_index,
    }


def grid_search_result_from_jsonb(data: dict[str, Any]) -> GridSearchResult:
    """JSONB dict → GridSearchResult (test / detail rendering 용)."""
    param_names = tuple(data["param_names"])
    param_values: dict[str, tuple[Decimal, ...]] = {
        k: tuple(Decimal(v) for v in vs)
        for k, vs in data["param_values"].items()
    }
    cells_t = tuple(
        GridSearchCell(
            param_values={
                k: Decimal(v) for k, v in c["param_values"].items()
            },
            sharpe=None if c.get("sharpe") is None else Decimal(c["sharpe"]),
            total_return=Decimal(c["total_return"]),
            max_drawdown=Decimal(c["max_drawdown"]),
            num_trades=int(c["num_trades"]),
            is_degenerate=bool(c["is_degenerate"]),
            objective_value=(
                None if c.get("objective_value") is None
                else Decimal(c["objective_value"])
            ),
        )
        for c in data["cells"]
    )
    return GridSearchResult(
        param_names=param_names,
        param_values=param_values,
        cells=cells_t,
        objective_metric=data["objective_metric"],
        direction=data["direction"],
        best_cell_index=data.get("best_cell_index"),
    )


def bayesian_search_result_to_jsonb(r: BayesianSearchResult) -> dict[str, Any]:
    """BayesianSearchResult → JSONB dict (schema_version=2).

    의무 (Sprint 55 plan §6.2 = Sprint 50/51/52 retro-incorrect 차단 4종):
        1. Decimal → str (FE Number.parseFloat 가능 표기 ``^-?\\d+(\\.\\d+)?$``).
        2. None 보존 (degenerate ``objective_value=null`` 명시 필드).
        3. iteration row insertion order 보존 (Python list 순서 = idx 순서).
        4. ``best_iteration_idx`` 명시 필드 (FE highlight 용, search 재실행 X).
    """
    return {
        "schema_version": 2,
        "kind": "bayesian",
        "param_names": list(r.param_names),
        "iterations": [
            {
                "idx": it.idx,
                "params": {k: str(v) for k, v in it.params.items()},
                "objective_value": (
                    None if it.objective_value is None else str(it.objective_value)
                ),
                "best_so_far": (
                    None if it.best_so_far is None else str(it.best_so_far)
                ),
                "is_degenerate": it.is_degenerate,
                "phase": it.phase,
            }
            for it in r.iterations
        ],
        "best_params": (
            None
            if r.best_params is None
            else {k: str(v) for k, v in r.best_params.items()}
        ),
        "best_objective_value": (
            None if r.best_objective_value is None else str(r.best_objective_value)
        ),
        "best_iteration_idx": r.best_iteration_idx,
        "objective_metric": r.objective_metric,
        "direction": r.direction,
        "bayesian_acquisition": r.bayesian_acquisition,
        "bayesian_n_initial_random": r.bayesian_n_initial_random,
        "max_evaluations": r.max_evaluations,
        "degenerate_count": r.degenerate_count,
        "total_iterations": r.total_iterations,
    }


def bayesian_search_result_from_jsonb(data: dict[str, Any]) -> BayesianSearchResult:
    """JSONB dict → BayesianSearchResult (test / detail rendering 용)."""
    param_names = tuple(data["param_names"])
    iterations_t = tuple(
        BayesianIteration(
            idx=int(it["idx"]),
            params={k: Decimal(v) for k, v in it["params"].items()},
            objective_value=(
                None if it.get("objective_value") is None else Decimal(it["objective_value"])
            ),
            best_so_far=(
                None if it.get("best_so_far") is None else Decimal(it["best_so_far"])
            ),
            is_degenerate=bool(it["is_degenerate"]),
            phase=it["phase"],
        )
        for it in data["iterations"]
    )
    return BayesianSearchResult(
        param_names=param_names,
        iterations=iterations_t,
        best_params=(
            None
            if data.get("best_params") is None
            else {k: Decimal(v) for k, v in data["best_params"].items()}
        ),
        best_objective_value=(
            None
            if data.get("best_objective_value") is None
            else Decimal(data["best_objective_value"])
        ),
        best_iteration_idx=data.get("best_iteration_idx"),
        objective_metric=data["objective_metric"],
        direction=data["direction"],
        bayesian_acquisition=data["bayesian_acquisition"],
        bayesian_n_initial_random=int(data["bayesian_n_initial_random"]),
        max_evaluations=int(data["max_evaluations"]),
        degenerate_count=int(data["degenerate_count"]),
        total_iterations=int(data["total_iterations"]),
    )

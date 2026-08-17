"""Optimizer JSONB 직렬화 helpers — GridSearchResult / BayesianSearchResult ↔ JSONB dict.

Decimal → str, None 보존, row-major iterations / cells 보존. stress_test/serializers.py mirror.

Sprint 55 = BayesianSearchResult 추가. top-level ``kind`` 필드 echo (FE
z.discriminatedUnion("kind") 의무) + ``best_iteration_idx`` 명시 (Sprint 50/51/52
retro-incorrect 패턴 차단).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from src.optimizer.engine import (
    BayesianIteration,
    BayesianSearchResult,
    GeneticIndividual,
    GeneticSearchResult,
    GridSearchCell,
    GridSearchResult,
)
from src.optimizer.engine.select import OptimizerResult


def optimizer_result_to_jsonb(result: OptimizerResult) -> dict[str, Any]:
    """kind 무관 단일 직렬화 진입점 — service._execute 소비 (deepen A).

    engine.select.run_optimizer_by_kind 와 짝을 이뤄 "runner → serializer 페어링"
    분기가 서비스에 재등장하지 않도록 한다. 새 알고리즘 추가 시 여기 1곳만 확장.
    """
    if isinstance(result, GridSearchResult):
        return grid_search_result_to_jsonb(result)
    if isinstance(result, BayesianSearchResult):
        return bayesian_search_result_to_jsonb(result)
    if isinstance(result, GeneticSearchResult):
        return genetic_search_result_to_jsonb(result)
    raise TypeError(f"Unsupported optimizer result type: {type(result)!r}")


def best_metrics_from_jsonb(
    result: dict[str, Any] | None,
) -> tuple[Decimal | None, Decimal | None]:
    """저장된 result JSONB → best 조합의 (total_return, max_drawdown). [BL-429]

    목록 응답이 최적화 행에도 백테스트 행과 **같은 의미의 숫자**를 실을 수 있게 하는 SSOT.
    kind 별로 값이 있는 자리가 다르다 — grid 는 best cell 안, bayesian/genetic 은 요약 블록.

    ★값이 없으면 (None, None) 이다. 「없음」과 「0」은 다르고, 화면이 그 둘을 구분해야 한다:
    RUNNING·FAILED(result 없음) · 전건 degenerate(best 미확정) · BL-429 이전 저장 row.

    손상 row 방어: Sprint 50-52 retro-incorrect row 가 실재하므로 모양이 어긋나면
    예외 대신 (None, None) 을 낸다. `Decimal` 의 `InvalidOperation` 은 `ValueError` 가
    아니라 `ArithmeticError` 라 service 의 `_to_response_or_none` 이 못 잡는다.
    """
    if not isinstance(result, dict):
        return None, None
    kind = result.get("kind")
    if kind == "grid_search":
        cells = result.get("cells")
        idx = result.get("best_cell_index")
        if not isinstance(cells, list) or not isinstance(idx, int) or not 0 <= idx < len(cells):
            return None, None
        best = cells[idx]
        if not isinstance(best, dict):
            return None, None
        return _to_decimal_or_none(best.get("total_return")), _to_decimal_or_none(
            best.get("max_drawdown")
        )
    if kind in ("bayesian", "genetic"):
        return _to_decimal_or_none(result.get("best_total_return")), _to_decimal_or_none(
            result.get("best_max_drawdown")
        )
    return None, None


def _to_decimal_or_none(raw: Any) -> Decimal | None:
    """직렬화된 decimal 문자열 → Decimal. 모양이 어긋나면 None (손상 row 방어)."""
    if not isinstance(raw, str):
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _iteration_common_to_jsonb(it: BayesianIteration | GeneticIndividual) -> dict[str, Any]:
    """iteration 공통 5키 직렬화 — Decimal→str, None 보존 (deepen B, SSOT).

    bayesian 은 phase, genetic 은 generation 을 caller 가 6번째 키로 추가한다.
    """
    return {
        "idx": it.idx,
        "params": {k: str(v) for k, v in it.params.items()},
        "objective_value": (None if it.objective_value is None else str(it.objective_value)),
        "best_so_far": None if it.best_so_far is None else str(it.best_so_far),
        "is_degenerate": it.is_degenerate,
    }


def _iteration_common_from_jsonb(it: dict[str, Any]) -> dict[str, Any]:
    """iteration 공통 5키 역직렬화 — dataclass kwargs 로 반환."""
    return {
        "idx": int(it["idx"]),
        "params": {k: Decimal(v) for k, v in it["params"].items()},
        "objective_value": (
            None if it.get("objective_value") is None else Decimal(it["objective_value"])
        ),
        "best_so_far": (None if it.get("best_so_far") is None else Decimal(it["best_so_far"])),
        "is_degenerate": bool(it["is_degenerate"]),
    }


def _search_summary_to_jsonb(
    r: BayesianSearchResult | GeneticSearchResult,
) -> dict[str, Any]:
    """best 블록 + objective/direction 공통 직렬화 (bayesian ≡ genetic)."""
    return {
        "best_params": (
            None if r.best_params is None else {k: str(v) for k, v in r.best_params.items()}
        ),
        "best_objective_value": (
            None if r.best_objective_value is None else str(r.best_objective_value)
        ),
        "best_iteration_idx": r.best_iteration_idx,
        # BL-429 — best 의 백테스트 metric. schema_version 은 올리지 않는다(순수 추가 필드).
        "best_total_return": (None if r.best_total_return is None else str(r.best_total_return)),
        "best_max_drawdown": (None if r.best_max_drawdown is None else str(r.best_max_drawdown)),
        "objective_metric": r.objective_metric,
        "direction": r.direction,
    }


def _search_summary_from_jsonb(data: dict[str, Any]) -> dict[str, Any]:
    """best 블록 + objective/direction 공통 역직렬화 — dataclass kwargs 로 반환."""
    return {
        "best_params": (
            None
            if data.get("best_params") is None
            else {k: Decimal(v) for k, v in data["best_params"].items()}
        ),
        "best_objective_value": (
            None
            if data.get("best_objective_value") is None
            else Decimal(data["best_objective_value"])
        ),
        "best_iteration_idx": data.get("best_iteration_idx"),
        # BL-429 이전에 저장된 row 는 두 키가 없다 — 그때는 None 이 정답이다(0 이 아니다).
        "best_total_return": (
            None if data.get("best_total_return") is None else Decimal(data["best_total_return"])
        ),
        "best_max_drawdown": (
            None if data.get("best_max_drawdown") is None else Decimal(data["best_max_drawdown"])
        ),
        "objective_metric": data["objective_metric"],
        "direction": data["direction"],
    }


def grid_search_result_to_jsonb(r: GridSearchResult) -> dict[str, Any]:
    """GridSearchResult → JSONB dict. Decimal → str, cells row-major flatten.

    Sprint 55 = top-level ``kind: "grid_search"`` echo (FE discriminated union 의무).
    """
    return {
        "schema_version": 1,
        "kind": "grid_search",
        "param_names": list(r.param_names),
        "param_values": {k: [str(v) for v in vs] for k, vs in r.param_values.items()},
        "cells": [
            {
                "param_values": {k: str(v) for k, v in c.param_values.items()},
                "sharpe": None if c.sharpe is None else str(c.sharpe),
                "total_return": str(c.total_return),
                "max_drawdown": str(c.max_drawdown),
                "num_trades": c.num_trades,
                "is_degenerate": c.is_degenerate,
                "objective_value": (None if c.objective_value is None else str(c.objective_value)),
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
        k: tuple(Decimal(v) for v in vs) for k, vs in data["param_values"].items()
    }
    cells_t = tuple(
        GridSearchCell(
            param_values={k: Decimal(v) for k, v in c["param_values"].items()},
            sharpe=None if c.get("sharpe") is None else Decimal(c["sharpe"]),
            total_return=Decimal(c["total_return"]),
            max_drawdown=Decimal(c["max_drawdown"]),
            num_trades=int(c["num_trades"]),
            is_degenerate=bool(c["is_degenerate"]),
            objective_value=(
                None if c.get("objective_value") is None else Decimal(c["objective_value"])
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
            {**_iteration_common_to_jsonb(it), "phase": it.phase} for it in r.iterations
        ],
        **_search_summary_to_jsonb(r),
        "bayesian_acquisition": r.bayesian_acquisition,
        "bayesian_n_initial_random": r.bayesian_n_initial_random,
        "max_evaluations": r.max_evaluations,
        "degenerate_count": r.degenerate_count,
        "total_iterations": r.total_iterations,
    }


def bayesian_search_result_from_jsonb(data: dict[str, Any]) -> BayesianSearchResult:
    """JSONB dict → BayesianSearchResult (test / detail rendering 용)."""
    iterations_t = tuple(
        BayesianIteration(**_iteration_common_from_jsonb(it), phase=it["phase"])
        for it in data["iterations"]
    )
    return BayesianSearchResult(
        param_names=tuple(data["param_names"]),
        iterations=iterations_t,
        **_search_summary_from_jsonb(data),
        bayesian_acquisition=data["bayesian_acquisition"],
        bayesian_n_initial_random=int(data["bayesian_n_initial_random"]),
        max_evaluations=int(data["max_evaluations"]),
        degenerate_count=int(data["degenerate_count"]),
        total_iterations=int(data["total_iterations"]),
    )


def genetic_search_result_to_jsonb(r: GeneticSearchResult) -> dict[str, Any]:
    """Sprint 56 BL-233 — GeneticSearchResult → JSONB dict (schema_version=2).

    의무 (Sprint 56 ADR-013 §7 amendment = Sprint 50/51/52 retro-incorrect 차단 4종 mirror):
        1. Decimal → str (FE Number.parseFloat 가능 표기 ``^-?\\d+(\\.\\d+)?$``).
        2. None 보존 (degenerate ``objective_value=null`` 명시 필드).
        3. iteration row insertion order 보존 (Python list = idx 순서 + generation 단조 증가).
        4. ``best_iteration_idx`` 명시 필드 (FE highlight 용, 재검색 X).
    """
    return {
        "schema_version": 2,
        "kind": "genetic",
        "param_names": list(r.param_names),
        "iterations": [
            {**_iteration_common_to_jsonb(it), "generation": it.generation} for it in r.iterations
        ],
        **_search_summary_to_jsonb(r),
        "population_size": r.population_size,
        "n_generations": r.n_generations,
        "mutation_rate": str(r.mutation_rate),
        "crossover_rate": str(r.crossover_rate),
        "max_evaluations": r.max_evaluations,
        "degenerate_count": r.degenerate_count,
        "total_iterations": r.total_iterations,
    }


def genetic_search_result_from_jsonb(data: dict[str, Any]) -> GeneticSearchResult:
    """JSONB dict → GeneticSearchResult (test / detail rendering 용)."""
    iterations_t = tuple(
        GeneticIndividual(**_iteration_common_from_jsonb(it), generation=int(it["generation"]))
        for it in data["iterations"]
    )
    return GeneticSearchResult(
        param_names=tuple(data["param_names"]),
        iterations=iterations_t,
        **_search_summary_from_jsonb(data),
        population_size=int(data["population_size"]),
        n_generations=int(data["n_generations"]),
        mutation_rate=Decimal(data["mutation_rate"]),
        crossover_rate=Decimal(data["crossover_rate"]),
        max_evaluations=int(data["max_evaluations"]),
        degenerate_count=int(data["degenerate_count"]),
        total_iterations=int(data["total_iterations"]),
    )

# optimizer serializer golden 스냅샷 — 리팩토링 byte-compat 증명 (deepen A+B)
"""Serializer JSONB 출력 golden 회귀.

optimizer-deepen B: bayesian≡genetic 4함수의 iteration/summary 공통부를 helper 로
추출하면서, 출력 JSONB 의 키 집합·값 표현(Decimal→str, None→null, kind echo,
schema_version)이 리팩토링 전과 1:1 동일함을 아래 golden dict 로 고정한다.
golden 은 리팩토링 이전 코드 출력에서 캡처 — 변경 시 FE zod strict parse 파손 신호.

추가로 optimizer_result_to_jsonb 단일 진입점(A: service._execute 소비)을 검증.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.optimizer.engine import (
    BayesianIteration,
    BayesianSearchResult,
    GeneticIndividual,
    GeneticSearchResult,
    GridSearchCell,
    GridSearchResult,
)
from src.optimizer.serializers import (
    bayesian_search_result_from_jsonb,
    bayesian_search_result_to_jsonb,
    genetic_search_result_from_jsonb,
    genetic_search_result_to_jsonb,
    grid_search_result_from_jsonb,
    grid_search_result_to_jsonb,
)


def _grid_result() -> GridSearchResult:
    return GridSearchResult(
        param_names=("ema", "stop"),
        param_values={
            "ema": (Decimal(10), Decimal(20)),
            "stop": (Decimal("0.5"),),
        },
        cells=(
            GridSearchCell(
                param_values={"ema": Decimal(10), "stop": Decimal("0.5")},
                sharpe=Decimal("1.5"),
                total_return=Decimal("0.12"),
                max_drawdown=Decimal("-0.05"),
                num_trades=5,
                is_degenerate=False,
                objective_value=Decimal("1.5"),
            ),
            GridSearchCell(
                param_values={"ema": Decimal(20), "stop": Decimal("0.5")},
                sharpe=None,
                total_return=Decimal("0"),
                max_drawdown=Decimal("0"),
                num_trades=0,
                is_degenerate=True,
                objective_value=None,
            ),
        ),
        objective_metric="sharpe_ratio",
        direction="maximize",
        best_cell_index=0,
    )


def _bayesian_result() -> BayesianSearchResult:
    return BayesianSearchResult(
        param_names=("ema",),
        iterations=(
            BayesianIteration(
                idx=0,
                params={"ema": Decimal("14")},
                objective_value=Decimal("1.5"),
                best_so_far=Decimal("1.5"),
                is_degenerate=False,
                phase="random",
            ),
            BayesianIteration(
                idx=1,
                params={"ema": Decimal("21")},
                objective_value=None,
                best_so_far=Decimal("1.5"),
                is_degenerate=True,
                phase="acquisition",
            ),
        ),
        best_params={"ema": Decimal("14")},
        best_objective_value=Decimal("1.5"),
        best_iteration_idx=0,
        objective_metric="sharpe_ratio",
        direction="maximize",
        bayesian_acquisition="EI",
        bayesian_n_initial_random=2,
        max_evaluations=5,
        degenerate_count=1,
        total_iterations=2,
    )


def _genetic_result() -> GeneticSearchResult:
    return GeneticSearchResult(
        param_names=("ema",),
        iterations=(
            GeneticIndividual(
                idx=0,
                params={"ema": Decimal("12")},
                objective_value=Decimal("0.9"),
                best_so_far=Decimal("0.9"),
                is_degenerate=False,
                generation=0,
            ),
            GeneticIndividual(
                idx=1,
                params={"ema": Decimal("25")},
                objective_value=None,
                best_so_far=Decimal("0.9"),
                is_degenerate=True,
                generation=1,
            ),
        ),
        best_params={"ema": Decimal("12")},
        best_objective_value=Decimal("0.9"),
        best_iteration_idx=0,
        objective_metric="sharpe_ratio",
        direction="maximize",
        population_size=4,
        n_generations=3,
        mutation_rate=Decimal("0.1"),
        crossover_rate=Decimal("0.8"),
        max_evaluations=12,
        degenerate_count=1,
        total_iterations=2,
    )


GRID_GOLDEN = {
    "schema_version": 1,
    "kind": "grid_search",
    "param_names": ["ema", "stop"],
    "param_values": {"ema": ["10", "20"], "stop": ["0.5"]},
    "cells": [
        {
            "param_values": {"ema": "10", "stop": "0.5"},
            "sharpe": "1.5",
            "total_return": "0.12",
            "max_drawdown": "-0.05",
            "num_trades": 5,
            "is_degenerate": False,
            "objective_value": "1.5",
        },
        {
            "param_values": {"ema": "20", "stop": "0.5"},
            "sharpe": None,
            "total_return": "0",
            "max_drawdown": "0",
            "num_trades": 0,
            "is_degenerate": True,
            "objective_value": None,
        },
    ],
    "objective_metric": "sharpe_ratio",
    "direction": "maximize",
    "best_cell_index": 0,
}

BAYESIAN_GOLDEN = {
    "schema_version": 2,
    "kind": "bayesian",
    "param_names": ["ema"],
    "iterations": [
        {
            "idx": 0,
            "params": {"ema": "14"},
            "objective_value": "1.5",
            "best_so_far": "1.5",
            "is_degenerate": False,
            "phase": "random",
        },
        {
            "idx": 1,
            "params": {"ema": "21"},
            "objective_value": None,
            "best_so_far": "1.5",
            "is_degenerate": True,
            "phase": "acquisition",
        },
    ],
    "best_params": {"ema": "14"},
    "best_objective_value": "1.5",
    "best_iteration_idx": 0,
    "objective_metric": "sharpe_ratio",
    "direction": "maximize",
    "bayesian_acquisition": "EI",
    "bayesian_n_initial_random": 2,
    "max_evaluations": 5,
    "degenerate_count": 1,
    "total_iterations": 2,
}

GENETIC_GOLDEN = {
    "schema_version": 2,
    "kind": "genetic",
    "param_names": ["ema"],
    "iterations": [
        {
            "idx": 0,
            "params": {"ema": "12"},
            "objective_value": "0.9",
            "best_so_far": "0.9",
            "is_degenerate": False,
            "generation": 0,
        },
        {
            "idx": 1,
            "params": {"ema": "25"},
            "objective_value": None,
            "best_so_far": "0.9",
            "is_degenerate": True,
            "generation": 1,
        },
    ],
    "best_params": {"ema": "12"},
    "best_objective_value": "0.9",
    "best_iteration_idx": 0,
    "objective_metric": "sharpe_ratio",
    "direction": "maximize",
    "population_size": 4,
    "n_generations": 3,
    "mutation_rate": "0.1",
    "crossover_rate": "0.8",
    "max_evaluations": 12,
    "degenerate_count": 1,
    "total_iterations": 2,
}


# --- golden: 출력 dict 완전 일치 (키 집합 + 값 표현) ---


def test_grid_to_jsonb_matches_golden() -> None:
    assert grid_search_result_to_jsonb(_grid_result()) == GRID_GOLDEN


def test_bayesian_to_jsonb_matches_golden() -> None:
    assert bayesian_search_result_to_jsonb(_bayesian_result()) == BAYESIAN_GOLDEN


def test_genetic_to_jsonb_matches_golden() -> None:
    assert genetic_search_result_to_jsonb(_genetic_result()) == GENETIC_GOLDEN


# --- round-trip: to_jsonb → from_jsonb 완전 복원 ---


def test_grid_round_trip() -> None:
    restored = grid_search_result_from_jsonb(grid_search_result_to_jsonb(_grid_result()))
    assert restored == _grid_result()


def test_bayesian_round_trip() -> None:
    restored = bayesian_search_result_from_jsonb(
        bayesian_search_result_to_jsonb(_bayesian_result())
    )
    assert restored == _bayesian_result()


def test_genetic_round_trip() -> None:
    restored = genetic_search_result_from_jsonb(
        genetic_search_result_to_jsonb(_genetic_result())
    )
    assert restored == _genetic_result()


# --- 단일 진입점 (A: service._execute 소비) ---


def test_optimizer_result_to_jsonb_routes_by_type() -> None:
    from src.optimizer.serializers import optimizer_result_to_jsonb

    assert optimizer_result_to_jsonb(_grid_result()) == GRID_GOLDEN
    assert optimizer_result_to_jsonb(_bayesian_result()) == BAYESIAN_GOLDEN
    assert optimizer_result_to_jsonb(_genetic_result()) == GENETIC_GOLDEN


def test_optimizer_result_to_jsonb_rejects_unknown_type() -> None:
    from src.optimizer.serializers import optimizer_result_to_jsonb

    with pytest.raises(TypeError):
        optimizer_result_to_jsonb(object())  # type: ignore[arg-type]

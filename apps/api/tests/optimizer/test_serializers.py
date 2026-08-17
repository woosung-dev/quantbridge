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
    best_metrics_from_jsonb,
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
        best_total_return=Decimal("0.31"),
        best_max_drawdown=Decimal("-0.08"),
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
        best_total_return=Decimal("0.24"),
        best_max_drawdown=Decimal("-0.11"),
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
    "best_total_return": "0.31",
    "best_max_drawdown": "-0.08",
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
    "best_total_return": "0.24",
    "best_max_drawdown": "-0.11",
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
    restored = genetic_search_result_from_jsonb(genetic_search_result_to_jsonb(_genetic_result()))
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


# --- [BL-429] best 조합의 백테스트 metric 추출 ---


def test_best_metrics_grid_reads_best_cell() -> None:
    """grid 는 best cell 안에 값이 있다 — 다른 cell 의 값을 집으면 안 된다."""
    jsonb = grid_search_result_to_jsonb(_grid_result())
    assert best_metrics_from_jsonb(jsonb) == (Decimal("0.12"), Decimal("-0.05"))


def test_best_metrics_bayesian_and_genetic_read_summary_block() -> None:
    assert best_metrics_from_jsonb(bayesian_search_result_to_jsonb(_bayesian_result())) == (
        Decimal("0.31"),
        Decimal("-0.08"),
    )
    assert best_metrics_from_jsonb(genetic_search_result_to_jsonb(_genetic_result())) == (
        Decimal("0.24"),
        Decimal("-0.11"),
    )


@pytest.mark.parametrize(
    "jsonb",
    [
        pytest.param(None, id="result_none_running_or_failed"),
        pytest.param(
            {"kind": "grid_search", "cells": [], "best_cell_index": None}, id="grid_no_best"
        ),
        pytest.param(
            {"kind": "bayesian", "best_total_return": None, "best_max_drawdown": None},
            id="bayesian_all_degenerate",
        ),
        # BL-429 이전에 저장된 row — 두 키 자체가 없다. 0 이 아니라 None 이어야 한다.
        pytest.param({"kind": "bayesian", "best_objective_value": "1.5"}, id="legacy_row_no_keys"),
        pytest.param({"kind": "genetic", "best_objective_value": "0.9"}, id="legacy_genetic_row"),
        # 손상 row 방어 — Decimal 의 InvalidOperation 은 ValueError 가 아니라
        # ArithmeticError 라 service 의 _to_response_or_none 이 못 잡는다.
        pytest.param(
            {"kind": "grid_search", "cells": [{}], "best_cell_index": 0}, id="cell_missing_keys"
        ),
        pytest.param(
            {"kind": "grid_search", "cells": [{"total_return": "n/a"}], "best_cell_index": 0},
            id="cell_non_decimal_string",
        ),
        pytest.param(
            {"kind": "grid_search", "cells": [], "best_cell_index": 3}, id="index_out_of_range"
        ),
        pytest.param({"kind": "unknown_future_kind"}, id="unknown_kind"),
    ],
)
def test_best_metrics_absent_is_none_not_zero(jsonb: dict[str, object] | None) -> None:
    """★「없음」과 「0」은 다르다 — 0 을 내면 화면이 파산한 실행을 「손익 0」으로 그린다."""
    assert best_metrics_from_jsonb(jsonb) == (None, None)


def test_legacy_row_round_trip_keeps_none() -> None:
    """구 row 를 dataclass 로 되살려도 두 필드는 None 이다 (0 으로 채우지 않는다)."""
    legacy = bayesian_search_result_to_jsonb(_bayesian_result())
    del legacy["best_total_return"]
    del legacy["best_max_drawdown"]
    restored = bayesian_search_result_from_jsonb(legacy)
    assert restored.best_total_return is None
    assert restored.best_max_drawdown is None


# ── [BL-429] codex 적대 리뷰 P1 회귀 (2026-08-17) ──────────────────────────────
# 세 축 전부 **실제로 재현된 뒤** 수리됐다. 재현 없이 붙인 방어가 아니다.


def test_best_metrics_reject_bool_cell_index() -> None:
    """★`bool` 은 `int` 의 하위형이라 `cells[True]` 가 `cells[1]` 로 조용히 통과했다.

    수리 전 실측: `(Decimal("0.99"), Decimal("-0.01"))` — 두 번째 cell 을 best 라 불렀다.
    """
    corrupt = {
        "kind": "grid_search",
        "best_cell_index": True,
        "cells": [
            {"total_return": "0.10", "max_drawdown": "-0.50"},
            {"total_return": "0.99", "max_drawdown": "-0.01"},
        ],
    }
    assert best_metrics_from_jsonb(corrupt) == (None, None)

    # ★음성 대조 — `0` 을 `False` 로 오판해서 정상 row 를 죽이면 안 된다.
    healthy = {
        "kind": "grid_search",
        "best_cell_index": 0,
        "cells": [{"total_return": "0.10", "max_drawdown": "-0.50"}],
    }
    assert best_metrics_from_jsonb(healthy) == (Decimal("0.10"), Decimal("-0.50"))


@pytest.mark.parametrize(
    ("raw_total", "raw_mdd"),
    [
        pytest.param("0.20", "n/a", id="mdd_corrupt"),
        pytest.param("n/a", "-0.05", id="total_corrupt"),
        pytest.param("0.20", None, id="mdd_missing"),
    ],
)
def test_best_metrics_are_atomic(raw_total: object, raw_mdd: object) -> None:
    """한쪽만 파싱되면 둘 다 None 이다.

    수익률만 있고 MDD 가 빈 행은 「위험을 못 재는 성과」다 — 화면에서 위험 과소평가를 만든다.
    수리 전 실측: `("0.20", "n/a")` → `(Decimal("0.20"), None)`.
    """
    jsonb = {
        "kind": "grid_search",
        "best_cell_index": 0,
        "cells": [{"total_return": raw_total, "max_drawdown": raw_mdd}],
    }
    assert best_metrics_from_jsonb(jsonb) == (None, None)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_best_metrics_reject_non_finite(raw: str) -> None:
    """`Decimal("NaN")`·`Decimal("Infinity")` 는 `InvalidOperation` 을 안 낸다.

    통과시키면 응답 스키마의 유한성 검증에서 `ValidationError` 가 나고 service 가 그 행을
    통째로 None 으로 바꾼다 — 손상 셀 하나가 **목록에서 행을 지우고 상세를 404 로** 만든다.
    """
    assert best_metrics_from_jsonb(
        {"kind": "bayesian", "best_total_return": raw, "best_max_drawdown": "-0.1"}
    ) == (None, None)
    assert best_metrics_from_jsonb(
        {"kind": "genetic", "best_total_return": "0.1", "best_max_drawdown": raw}
    ) == (None, None)

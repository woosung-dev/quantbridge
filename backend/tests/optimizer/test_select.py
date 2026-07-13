# Optimizer kind-dispatch SSOT 테스트 — run_optimizer_by_kind 라우팅 + best_params_of 추출.
from __future__ import annotations

from decimal import Decimal

from src.optimizer.engine import (
    BayesianSearchResult,
    GeneticSearchResult,
    GridSearchCell,
    GridSearchResult,
)
from src.optimizer.engine import select as select_mod
from src.optimizer.engine.select import best_params_of, run_optimizer_by_kind
from src.optimizer.models import OptimizationKind


def _grid_result(*, best_cell_index: int | None) -> GridSearchResult:
    cells = (
        GridSearchCell(
            param_values={"ema": Decimal("5")},
            sharpe=Decimal("0.5"),
            total_return=Decimal("0.1"),
            max_drawdown=Decimal("-0.02"),
            num_trades=10,
            is_degenerate=False,
            objective_value=Decimal("0.5"),
        ),
        GridSearchCell(
            param_values={"ema": Decimal("20")},
            sharpe=Decimal("1.8"),
            total_return=Decimal("0.3"),
            max_drawdown=Decimal("-0.01"),
            num_trades=12,
            is_degenerate=False,
            objective_value=Decimal("1.8"),
        ),
    )
    return GridSearchResult(
        param_names=("ema",),
        param_values={"ema": (Decimal("5"), Decimal("20"))},
        cells=cells,
        objective_metric="sharpe_ratio",
        direction="maximize",
        best_cell_index=best_cell_index,
    )


def _bayesian_result(*, best_params: dict[str, Decimal] | None) -> BayesianSearchResult:
    return BayesianSearchResult(
        param_names=("ema",),
        iterations=(),
        best_params=best_params,
        best_objective_value=Decimal("1.0"),
        best_iteration_idx=0,
        objective_metric="sharpe_ratio",
        direction="maximize",
        bayesian_acquisition="EI",
        bayesian_n_initial_random=3,
        max_evaluations=10,
        degenerate_count=0,
        total_iterations=10,
    )


def _genetic_result(*, best_params: dict[str, Decimal] | None) -> GeneticSearchResult:
    return GeneticSearchResult(
        param_names=("ema",),
        iterations=(),
        best_params=best_params,
        best_objective_value=Decimal("1.0"),
        best_iteration_idx=0,
        objective_metric="sharpe_ratio",
        direction="maximize",
        population_size=6,
        n_generations=3,
        mutation_rate=Decimal("0.1"),
        crossover_rate=Decimal("0.8"),
        max_evaluations=10,
        degenerate_count=0,
        total_iterations=10,
    )


class TestBestParamsOf:
    def test_grid_returns_best_cell_param_values(self) -> None:
        assert best_params_of(_grid_result(best_cell_index=1)) == {"ema": Decimal("20")}

    def test_grid_none_when_no_best_cell(self) -> None:
        assert best_params_of(_grid_result(best_cell_index=None)) is None

    def test_bayesian_passthrough(self) -> None:
        assert best_params_of(_bayesian_result(best_params={"ema": Decimal("14")})) == {
            "ema": Decimal("14")
        }

    def test_bayesian_none(self) -> None:
        assert best_params_of(_bayesian_result(best_params=None)) is None

    def test_genetic_passthrough(self) -> None:
        assert best_params_of(_genetic_result(best_params={"ema": Decimal("9")})) == {
            "ema": Decimal("9")
        }


class TestRunOptimizerByKind:
    def test_grid_route_passes_args(self, monkeypatch) -> None:
        captured: dict[str, object] = {}

        def fake_grid(pine, ohlcv, *, param_space, backtest_config=None):  # type: ignore[no-untyped-def]
            captured["args"] = (pine, ohlcv, param_space, backtest_config)
            return "GRID"

        monkeypatch.setattr(select_mod, "run_grid_search", fake_grid)
        out = run_optimizer_by_kind(
            OptimizationKind.GRID_SEARCH,
            "pine",
            "ohlcv",
            param_space="PS",
            backtest_config="CFG",
        )
        assert out == "GRID"
        assert captured["args"] == ("pine", "ohlcv", "PS", "CFG")

    def test_bayesian_route(self, monkeypatch) -> None:
        monkeypatch.setattr(select_mod, "run_bayesian_search", lambda *a, **k: "BAYES")
        assert (
            run_optimizer_by_kind(OptimizationKind.BAYESIAN, "p", "o", param_space="PS")
            == "BAYES"
        )

    def test_genetic_route(self, monkeypatch) -> None:
        monkeypatch.setattr(select_mod, "run_genetic_search", lambda *a, **k: "GEN")
        assert (
            run_optimizer_by_kind(OptimizationKind.GENETIC, "p", "o", param_space="PS")
            == "GEN"
        )

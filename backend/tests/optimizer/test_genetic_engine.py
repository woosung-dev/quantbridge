# Sprint 56 — Optimizer Genetic engine unit tests (self-impl GA, mocked run_backtest).

from __future__ import annotations

import random
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from src.optimizer.engine.genetic import (
    _GENETIC_RANDOM_STATE,
    _MAX_GENETIC_EVALUATIONS,
    _TOURNAMENT_SIZE,
    GeneticIndividual,
    _compare_for_selection,
    _gaussian_mutation,
    _objective_from_metrics,
    _pick_best_iteration_idx,
    _roulette_select,
    _sample_individual,
    _single_point_crossover,
    _tournament_select,
    _update_best_so_far,
    run_genetic_search,
)
from src.optimizer.exceptions import OptimizationObjectiveUnsupportedError
from src.optimizer.schemas import ParamSpace

PINE_WITH_INPUTS = """
//@version=5
strategy("Sprint 56 Genetic test")
emaPeriod = input.int(14, "EMA Period")
stopLossPct = input.float(1.0, "Stop Loss %")
ema = ta.ema(close, emaPeriod)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""


def _make_ohlcv(n: int = 100) -> pd.DataFrame:
    """tz-aware DatetimeIndex OHLCV (Bayesian test mirror)."""
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(n)],
            "high": [101.0 + i * 0.1 for i in range(n)],
            "low": [99.0 + i * 0.1 for i in range(n)],
            "close": [100.5 + i * 0.1 for i in range(n)],
            "volume": [1000.0] * n,
        },
        index=idx,
    )


def _build_param_space(
    parameters: dict[str, Any],
    *,
    objective_metric: str = "sharpe_ratio",
    direction: str = "maximize",
    max_evaluations: int = 50,
    population_size: int | None = 5,
    n_generations: int | None = 4,
    mutation_rate: str | None = "0.2",
    crossover_rate: str | None = "0.8",
    schema_version: int = 2,
    genetic_selection_method: str | None = None,
) -> ParamSpace:
    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "objective_metric": objective_metric,
        "direction": direction,
        "max_evaluations": max_evaluations,
        "parameters": parameters,
    }
    if population_size is not None:
        payload["population_size"] = population_size
    if n_generations is not None:
        payload["n_generations"] = n_generations
    if mutation_rate is not None:
        payload["mutation_rate"] = mutation_rate
    if crossover_rate is not None:
        payload["crossover_rate"] = crossover_rate
    if genetic_selection_method is not None:
        payload["genetic_selection_method"] = genetic_selection_method
    return ParamSpace.model_validate(payload)


def _fake_outcome(
    *,
    sharpe: Decimal | None = Decimal("1.5"),
    total_return: Decimal = Decimal("0.2"),
    max_drawdown: Decimal = Decimal("0.05"),
    num_trades: int = 5,
) -> SimpleNamespace:
    metrics = SimpleNamespace(
        sharpe_ratio=sharpe,
        total_return=total_return,
        max_drawdown=max_drawdown,
        num_trades=num_trades,
    )
    result = SimpleNamespace(metrics=metrics)
    return SimpleNamespace(status="ok", result=result)


# === Section 1 — _sample_individual (deterministic seed) ===


class TestSampleIndividual:
    def test_integer_field_sampling_within_bounds(self) -> None:
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 5, "max": 30, "step": 1}}
        )
        rng = random.Random(_GENETIC_RANDOM_STATE)
        for _ in range(20):
            sample = _sample_individual(rng, space)
            assert 5 <= int(sample["x"]) <= 30

    def test_decimal_field_sampling_within_bounds(self) -> None:
        space = _build_param_space(
            {"y": {"kind": "decimal", "min": "0.1", "max": "2.0", "step": "0.1"}}
        )
        rng = random.Random(_GENETIC_RANDOM_STATE)
        for _ in range(20):
            sample = _sample_individual(rng, space)
            assert Decimal("0.1") <= sample["y"] <= Decimal("2.0")

    def test_deterministic_with_fixed_seed(self) -> None:
        """random_state=42 보장 결정성."""
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 0, "max": 100, "step": 1}}
        )
        rng1 = random.Random(_GENETIC_RANDOM_STATE)
        rng2 = random.Random(_GENETIC_RANDOM_STATE)
        s1 = _sample_individual(rng1, space)
        s2 = _sample_individual(rng2, space)
        assert s1 == s2


# === Section 2 — _tournament_select + _compare_for_selection ===


class TestCompareForSelection:
    def _ind(
        self, idx: int, obj: Decimal | None
    ) -> GeneticIndividual:
        return GeneticIndividual(
            idx=idx,
            params={"x": Decimal(idx)},
            objective_value=obj,
            best_so_far=obj,
            is_degenerate=obj is None,
            generation=0,
        )

    def test_non_degenerate_beats_degenerate(self) -> None:
        winner = _compare_for_selection(
            self._ind(0, None), self._ind(1, Decimal("0.5")), direction="maximize"
        )
        assert winner.idx == 1

    def test_maximize_picks_largest(self) -> None:
        winner = _compare_for_selection(
            self._ind(0, Decimal("1.0")), self._ind(1, Decimal("2.5")),
            direction="maximize",
        )
        assert winner.idx == 1

    def test_minimize_picks_smallest(self) -> None:
        winner = _compare_for_selection(
            self._ind(0, Decimal("1.0")), self._ind(1, Decimal("2.5")),
            direction="minimize",
        )
        assert winner.idx == 0


class TestTournamentSelect:
    def _pop(self, values: list[Decimal | None]) -> list[GeneticIndividual]:
        return [
            GeneticIndividual(
                idx=i,
                params={"x": Decimal(i)},
                objective_value=v,
                best_so_far=v,
                is_degenerate=v is None,
                generation=0,
            )
            for i, v in enumerate(values)
        ]

    def test_picks_best_in_tournament_maximize(self) -> None:
        pop = self._pop([Decimal("0.1"), Decimal("2.0"), Decimal("0.5"), Decimal("1.5")])
        # Tournament size 3 → 1 위 = 2.0 (idx=1)
        # Deterministic seed 으로 sampling 결과 검증
        rng = random.Random(0)
        wins = [_tournament_select(rng, pop, direction="maximize") for _ in range(20)]
        # 모든 결과는 pop 안 individual 중 하나여야 함.
        assert all(w in pop for w in wins)
        # 최소 1번 이상 best=2.0 선택되어야 함 (probabilistic 이지만 20번 안에는 확실).
        assert any(w.objective_value == Decimal("2.0") for w in wins)


# === Section 3 — _single_point_crossover ===


class TestSinglePointCrossover:
    def test_preserves_all_param_names(self) -> None:
        rng = random.Random(0)
        p1 = {"a": Decimal("1"), "b": Decimal("2"), "c": Decimal("3")}
        p2 = {"a": Decimal("10"), "b": Decimal("20"), "c": Decimal("30")}
        child = _single_point_crossover(rng, p1, p2, ("a", "b", "c"))
        assert set(child.keys()) == {"a", "b", "c"}

    def test_single_variable_returns_p1_clone(self) -> None:
        """n=1 = crossover 불가. p1 그대로 반환."""
        rng = random.Random(0)
        p1 = {"x": Decimal("1")}
        p2 = {"x": Decimal("2")}
        child = _single_point_crossover(rng, p1, p2, ("x",))
        assert child == {"x": Decimal("1")}

    def test_two_variables_cut_at_1(self) -> None:
        """n=2 → cut 만 1 가능. child[a]=p1, child[b]=p2."""
        rng = random.Random(0)
        p1 = {"a": Decimal("1"), "b": Decimal("2")}
        p2 = {"a": Decimal("10"), "b": Decimal("20")}
        child = _single_point_crossover(rng, p1, p2, ("a", "b"))
        assert child["a"] == Decimal("1")  # from p1
        assert child["b"] == Decimal("20")  # from p2


# === Section 4 — _gaussian_mutation ===


class TestGaussianMutation:
    def test_integer_field_clips_within_bounds(self) -> None:
        """gaussian mutation 결과 항상 [min, max] 안."""
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 5, "max": 30, "step": 1}}
        )
        rng = random.Random(0)
        params = {"x": Decimal("20")}
        for _ in range(50):
            mutated = _gaussian_mutation(
                rng, params, mutation_rate=Decimal("1.0"), param_space=space
            )
            assert Decimal(5) <= mutated["x"] <= Decimal(30)
            # banker's round = integer 값.
            assert mutated["x"] == Decimal(int(mutated["x"]))

    def test_decimal_field_clips_within_bounds(self) -> None:
        space = _build_param_space(
            {"y": {"kind": "decimal", "min": "0.1", "max": "2.0", "step": "0.1"}}
        )
        rng = random.Random(0)
        params = {"y": Decimal("1.0")}
        for _ in range(50):
            mutated = _gaussian_mutation(
                rng, params, mutation_rate=Decimal("1.0"), param_space=space
            )
            assert Decimal("0.1") <= mutated["y"] <= Decimal("2.0")


# === Section 5 — _objective_from_metrics + _update_best_so_far + _pick_best_iteration_idx ===


class TestObjectiveFromMetrics:
    def test_zero_trades_returns_none(self) -> None:
        metrics = SimpleNamespace(
            sharpe_ratio=Decimal("1.0"),
            total_return=Decimal("0"),
            max_drawdown=Decimal("0"),
            num_trades=0,
        )
        assert _objective_from_metrics(metrics, objective_metric="sharpe_ratio") is None

    def test_total_return_objective(self) -> None:
        metrics = SimpleNamespace(
            sharpe_ratio=Decimal("1.0"),
            total_return=Decimal("0.42"),
            max_drawdown=Decimal("0.1"),
            num_trades=5,
        )
        assert (
            _objective_from_metrics(metrics, objective_metric="total_return")
            == Decimal("0.42")
        )

    def test_unsupported_objective_raises(self) -> None:
        metrics = SimpleNamespace(
            sharpe_ratio=Decimal("1.0"),
            total_return=Decimal("0"),
            max_drawdown=Decimal("0"),
            num_trades=5,
        )
        with pytest.raises(OptimizationObjectiveUnsupportedError):
            _objective_from_metrics(metrics, objective_metric="calmar_ratio")


class TestUpdateBestSoFar:
    def test_maximize(self) -> None:
        assert _update_best_so_far(None, Decimal("1"), direction="maximize") == Decimal("1")
        assert _update_best_so_far(Decimal("1"), Decimal("2"), direction="maximize") == Decimal("2")
        assert _update_best_so_far(Decimal("3"), Decimal("2"), direction="maximize") == Decimal("3")

    def test_minimize(self) -> None:
        assert _update_best_so_far(Decimal("1"), Decimal("2"), direction="minimize") == Decimal("1")
        assert _update_best_so_far(Decimal("3"), Decimal("2"), direction="minimize") == Decimal("2")

    def test_degenerate_skipped(self) -> None:
        assert _update_best_so_far(Decimal("1"), None, direction="maximize") == Decimal("1")


class TestPickBestIterationIdx:
    def _it(
        self, idx: int, obj: Decimal | None, *, gen: int = 0
    ) -> GeneticIndividual:
        return GeneticIndividual(
            idx=idx,
            params={"x": Decimal(idx)},
            objective_value=obj,
            best_so_far=obj,
            is_degenerate=obj is None,
            generation=gen,
        )

    def test_maximize_picks_largest(self) -> None:
        its = (
            self._it(0, Decimal("1.0")),
            self._it(1, Decimal("2.5")),
            self._it(2, Decimal("0.5")),
        )
        assert _pick_best_iteration_idx(its, direction="maximize") == 1

    def test_minimize_picks_smallest(self) -> None:
        its = (
            self._it(0, Decimal("1.0")),
            self._it(1, Decimal("2.5")),
            self._it(2, Decimal("0.5")),
        )
        assert _pick_best_iteration_idx(its, direction="minimize") == 2

    def test_all_degenerate_returns_none(self) -> None:
        its = (self._it(0, None), self._it(1, None))
        assert _pick_best_iteration_idx(its, direction="maximize") is None


# === Section 6 — run_genetic_search validation + end-to-end ===


class TestRunGeneticSearchValidation:
    def test_schema_version_1_raises(self) -> None:
        # schema_version=1 with v2-only fields is rejected at ParamSpace level — skip.
        # 직접 minimal v1 space 만들고 run_genetic_search 가 다시 reject 하는지 검증.
        space = ParamSpace.model_validate(
            {
                "schema_version": 1,
                "objective_metric": "sharpe_ratio",
                "direction": "maximize",
                "max_evaluations": 50,
                "parameters": {
                    "x": {"kind": "integer", "min": 5, "max": 30, "step": 1},
                },
            }
        )
        with pytest.raises(ValueError, match="schema_version=2"):
            run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)

    def test_missing_population_size_raises(self) -> None:
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=None,
        )
        with pytest.raises(ValueError, match="population_size"):
            run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)

    def test_missing_crossover_rate_raises(self) -> None:
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            crossover_rate=None,
        )
        with pytest.raises(ValueError, match="crossover_rate"):
            run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)

    def test_budget_above_max_raises(self) -> None:
        # 10 * 6 = 60 > _MAX_GENETIC_EVALUATIONS (50)
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=10,
            n_generations=5,
            max_evaluations=60,
        )
        with pytest.raises(ValueError, match="exceeds server cap"):
            run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)

    def test_max_evaluations_below_budget_raises(self) -> None:
        # 5 * 5 = 25 budget, but max_evaluations=10
        space = _build_param_space(
            {"x": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=5,
            n_generations=4,
            max_evaluations=10,  # < budget=25
        )
        with pytest.raises(ValueError, match="max_evaluations"):
            run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)


class TestRunGeneticSearchEndToEnd:
    def test_end_to_end_with_mocked_backtest(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """population=4, generations=2 = 12 evaluations, sharpe=call counter."""
        call_count = {"n": 0}

        def fake_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            call_count["n"] += 1
            return _fake_outcome(sharpe=Decimal(call_count["n"]))

        monkeypatch.setattr(
            "src.optimizer.engine.genetic.run_backtest", fake_run_backtest
        )

        space = _build_param_space(
            {
                "emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1},
                "stopLossPct": {
                    "kind": "decimal", "min": "0.5", "max": "2.0", "step": "0.1"
                },
            },
            population_size=4,
            n_generations=2,
            max_evaluations=50,
        )
        result = run_genetic_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )

        # 4 * (2 + 1) = 12 evaluations.
        assert result.total_iterations == 12
        assert call_count["n"] == 12
        assert result.population_size == 4
        assert result.n_generations == 2
        # maximize + sharpe=counter → 마지막 호출 idx=11, sharpe=12.
        assert result.best_iteration_idx == 11
        assert result.best_objective_value == Decimal("12")
        assert result.degenerate_count == 0

    def test_end_to_end_minimize_with_degenerate_iterations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """minimize + 일부 cell num_trades=0 → degenerate skip + best=가장 작은 valid."""
        call_count = {"n": 0}

        def fake_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            call_count["n"] += 1
            # 짝수 call = degenerate, 홀수 call = sharpe = call counter
            if call_count["n"] % 2 == 0:
                return _fake_outcome(sharpe=None, num_trades=0)
            return _fake_outcome(sharpe=Decimal(call_count["n"]))

        monkeypatch.setattr(
            "src.optimizer.engine.genetic.run_backtest", fake_run_backtest
        )

        space = _build_param_space(
            {"emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=4,
            n_generations=1,
            max_evaluations=50,
            direction="minimize",
        )
        result = run_genetic_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )
        # 4 * 2 = 8 evaluations, 절반 degenerate
        assert result.total_iterations == 8
        assert result.degenerate_count == 4
        # minimize + 홀수 call sharpe = 1, 3, 5, 7 중 최소 = 1 (idx=0).
        assert result.best_objective_value == Decimal("1")
        assert result.best_iteration_idx == 0

    def test_deterministic_with_seed_repeats_same_iterations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """random_state=42 보장 동일 input → 동일 iteration param 시퀀스."""
        captured: list[dict[str, Decimal]] = []

        def fake_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            captured.append(dict(cfg.input_overrides or {}))
            return _fake_outcome(sharpe=Decimal("1.5"))

        monkeypatch.setattr(
            "src.optimizer.engine.genetic.run_backtest", fake_run_backtest
        )

        space = _build_param_space(
            {"emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=3,
            n_generations=1,
            max_evaluations=50,
        )
        run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)
        first_run = list(captured)
        captured.clear()
        run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)
        second_run = list(captured)
        assert first_run == second_run

    def test_empty_parameters_raises(self) -> None:
        space = _build_param_space(
            {},
            population_size=3,
            n_generations=1,
            max_evaluations=50,
        )
        with pytest.raises(ValueError, match="parameters must declare at least"):
            run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)


# === Section 7 — genetic_search_result_to_jsonb / from_jsonb round-trip ===


class TestSerializerRoundTrip:
    def test_to_jsonb_and_back_preserves_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """end-to-end + round-trip — Sprint 56 BL-233 JSONB shape 4종 차단 검증."""
        from src.optimizer.serializers import (
            genetic_search_result_from_jsonb,
            genetic_search_result_to_jsonb,
        )

        call_count = {"n": 0}

        def fake(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            call_count["n"] += 1
            n = call_count["n"]
            if n == 2:  # idx 1 = degenerate
                return _fake_outcome(num_trades=0, sharpe=None)
            return _fake_outcome(sharpe=Decimal(str(n * 0.5)))

        monkeypatch.setattr("src.optimizer.engine.genetic.run_backtest", fake)
        space = _build_param_space(
            {"emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=3,
            n_generations=1,
            max_evaluations=50,
        )
        result = run_genetic_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )
        jsonb = genetic_search_result_to_jsonb(result)

        # Sprint 56 ADR-013 §7 amendment 차단 4종 검증.
        # (1) Decimal → str.
        assert isinstance(jsonb["iterations"][0]["params"]["emaPeriod"], str)
        assert isinstance(jsonb["mutation_rate"], str)
        assert isinstance(jsonb["crossover_rate"], str)
        # (2) None 보존 (degenerate idx=1).
        assert jsonb["iterations"][1]["objective_value"] is None
        assert jsonb["iterations"][1]["is_degenerate"] is True
        # (3) iteration row insertion order — 3 * (1 + 1) = 6 evaluations.
        assert [it["idx"] for it in jsonb["iterations"]] == [0, 1, 2, 3, 4, 5]
        # (4) best_iteration_idx 명시.
        assert "best_iteration_idx" in jsonb
        # generation 필드 보존 (FE x-axis 가능).
        assert jsonb["iterations"][0]["generation"] == 0
        assert jsonb["iterations"][3]["generation"] == 1
        # top-level kind echo (FE z.discriminatedUnion 의무).
        assert jsonb["kind"] == "genetic"
        assert jsonb["schema_version"] == 2

        # round-trip.
        restored = genetic_search_result_from_jsonb(jsonb)
        assert restored.best_iteration_idx == result.best_iteration_idx
        assert restored.best_objective_value == result.best_objective_value
        assert restored.iterations[1].objective_value is None
        assert restored.iterations[1].is_degenerate
        assert restored.degenerate_count == result.degenerate_count
        assert restored.population_size == 3
        assert restored.n_generations == 1
        assert restored.mutation_rate == result.mutation_rate
        assert restored.crossover_rate == result.crossover_rate


def test_max_evaluations_constant_is_50() -> None:
    """plan §11 + ADR-013 §7 lock — Sprint 56 = 50 evaluation 상한."""
    assert _MAX_GENETIC_EVALUATIONS == 50


def test_tournament_size_default_is_3() -> None:
    """ADR-013 §7 amendment — tournament size=3 hard-coded default (Sprint 57+ enum 확장)."""
    assert _TOURNAMENT_SIZE == 3


# === Sprint 57 BL-234 — Genetic roulette selection ===


def _make_ind(
    idx: int,
    val: str | None,
    *,
    gen: int = 0,
    x_key: str = "x",
) -> GeneticIndividual:
    obj = Decimal(val) if val is not None else None
    return GeneticIndividual(
        idx=idx,
        params={x_key: obj or Decimal("0")},
        objective_value=obj,
        best_so_far=obj,
        is_degenerate=(val is None),
        generation=gen,
    )


class TestRoulettSelect:
    def test_returns_individual_from_population(self) -> None:
        rng = random.Random(42)
        pop = [_make_ind(0, "1.0"), _make_ind(1, "5.0"), _make_ind(2, "3.0")]
        result = _roulette_select(rng, pop, direction="maximize")
        assert result.params["x"] in [Decimal("1"), Decimal("5"), Decimal("3")]

    def test_all_degenerate_falls_back_to_random(self) -> None:
        rng = random.Random(42)
        pop = [_make_ind(0, None), _make_ind(1, None)]
        result = _roulette_select(rng, pop, direction="maximize")
        assert result in pop

    def test_single_non_degenerate_always_selected(self) -> None:
        rng = random.Random(99)
        pop = [
            _make_ind(0, "7.0"),
            _make_ind(1, None),
            _make_ind(2, None),
        ]
        for _ in range(10):
            result = _roulette_select(rng, pop, direction="maximize")
            assert result.params["x"] == Decimal("7")

    def test_minimize_direction_selects_lower_more_often(self) -> None:
        """minimize: 낮은 값 rank 높음 → 더 자주 선택됨."""
        rng = random.Random(0)
        low_ind = _make_ind(0, "1.0")
        high_ind = _make_ind(1, "100.0")
        pop = [low_ind, high_ind]
        counts: dict[str, int] = {"low": 0, "high": 0}
        for _ in range(200):
            result = _roulette_select(rng, pop, direction="minimize")
            if result.params["x"] == Decimal("1"):
                counts["low"] += 1
            else:
                counts["high"] += 1
        assert counts["low"] > counts["high"]


class TestRunGeneticSearchWithRoulette:
    def test_roulette_selection_method_completes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.optimizer.engine.genetic.run_backtest",
            lambda *a, **kw: _fake_outcome(),
        )
        ps = _build_param_space(
            {"emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=3,
            n_generations=2,
            max_evaluations=9,
            genetic_selection_method="roulette",
        )
        result = run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=ps)
        assert len(result.iterations) == 9

    def test_none_selection_method_defaults_to_tournament(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """genetic_selection_method=None → engine default tournament."""
        monkeypatch.setattr(
            "src.optimizer.engine.genetic.run_backtest",
            lambda *a, **kw: _fake_outcome(),
        )
        ps = _build_param_space(
            {"emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1}},
            population_size=3,
            n_generations=2,
            max_evaluations=9,
        )
        assert ps.genetic_selection_method is None
        result = run_genetic_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=ps)
        assert len(result.iterations) == 9

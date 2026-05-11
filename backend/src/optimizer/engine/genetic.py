# Optimizer Genetic executor — Sprint 56 BL-233, self-implementation GA (외부 dep 0).
"""Sprint 56 Phase 3 Optimizer Genetic executor.

ParamSpace (IntegerField + DecimalField + CategoricalField 재사용) → 단일 변수의 sampling
space + ParamSpace level hyperparam (population_size / n_generations / mutation_rate /
crossover_rate) 으로 진화. tournament select + single-point crossover + gaussian mutation
+ random_state=42 결정성.

자체 구현 채택 사유 (ADR-013 §7 amendment, Sprint 56):
  1. **외부 dep 0** — DEAP (LGPL-3) / PyGAD (numpy float lock) 둘 다 부적합. scikit-optimize
     (Bayesian) 와 달리 Genetic 은 our domain (Decimal/int discrete + continuous + 단일
     objective) 에 직접 fit 하는 단순 구현 (~250L) 으로 충분.
  2. **Decimal/int 직접 지원** — DEAP 는 float lock, our Decimal 정밀도 유지 위해 wrapper
     비용 증가.
  3. **결정성 강제** — `random.Random(_GENETIC_RANDOM_STATE)` 단일 인스턴스로 reproduce 보장.
  4. **확장성** — Sprint 57+ NSGA-II / multi-objective / island model 필요 시 DEAP 마이그레이션
     검토 가능 (현 시점 over-engineering).

서버 50 evaluation 강제 상한 (`_MAX_GENETIC_EVALUATIONS`): default queue + soft_time_limit
부재 시 worker block 위험. dedicated queue 는 Sprint 57+ BL-237. 실제 evaluation count =
``population_size * (n_generations + 1)`` (initial pop + 각 generation 의 새 offspring
재평가, 부모는 deterministic objective 가정 하에 재평가 생략).

direction=maximize/minimize — `_pick_best_iteration_idx` 와 cumulative `best_so_far` 양쪽
에서 동일 부호 처리. tournament select 도 direction 인자로 적절한 best 선출.

degenerate cell 처리 — outcome.status="ok" but metrics.sharpe_ratio is None /
num_trades=0 → objective_value=None + tournament 안 lowest-rank (penalty 동일). 비교 시
non-degenerate 우선 처리 (`_compare_individuals_for_selection`).

GeneticHyperparamsField 별도 신규 X — Bayesian 와 달리 variable level distribution 차이
없음. IntegerField / DecimalField / CategoricalField 재사용. ParamSpace level 만 4 신규
hyperparam (population_size / n_generations / mutation_rate / crossover_rate).

LESSON-019 (commit-spy): 본 executor 자체는 DB 미접근. Service 가 호출 결과를 result_jsonb
로 저장 + commit. spy 회귀는 Service test 책임.

LESSON-063 (deep-modules): `_build_cell_config` 같은 generic helper 는 Sprint 57+ 3-engine
도달 시 common 으로 추출 검토. 현재는 inline mirror 유지 (locality > DRY).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Any, Final, Literal

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig, BacktestMetrics
from src.optimizer.exceptions import (
    OptimizationExecutionError,
    OptimizationObjectiveUnsupportedError,
    OptimizationParameterUnsupportedError,
)
from src.optimizer.schemas import (
    CategoricalField,
    DecimalField,
    IntegerField,
    ParamSpace,
)
from src.strategy.pine_v2.coverage import analyze_coverage

# Sprint 57 BL-237 — optimizer_heavy queue 도입으로 50 → 100 relax.
# Sprint 56 이전: default queue 보호 목적 50 상한.
_MAX_GENETIC_EVALUATIONS: Final[int] = 100

# Sprint 56 — reproducibility 강제 random_state. 사용자 reseed 옵션 X (Sprint 57+ 확장 여지).
# Bayesian `_DEGENERATE_PENALTY` (skopt tell 전달용) 는 self-impl 에서 불필요 —
# tournament 안 degenerate 우선순위는 `_compare_for_selection` 으로 직접 처리.
_GENETIC_RANDOM_STATE: Final[int] = 42

# Sprint 56 — tournament size hard-coded default. Sprint 57+ enum 으로 확장 (selection_method).
_TOURNAMENT_SIZE: Final[int] = 3

# Sprint 56 — gaussian mutation sigma fraction = (max - min) * 본 값. 표준 GA 권고 = 0.1.
_MUTATION_SIGMA_FRACTION: Final[Decimal] = Decimal("0.1")

# Sprint 54 MVP mirror — BacktestMetrics 화이트리스트 (BL-236 Sprint 57+ 자유화).
_SUPPORTED_OBJECTIVE_METRICS: Final[frozenset[str]] = frozenset(
    {"sharpe_ratio", "total_return", "max_drawdown"}
)


@dataclass(frozen=True, slots=True)
class GeneticIndividual:
    """단일 GA evaluation — flat row (Bayesian iterations row-major mirror).

    `idx` 는 전체 search 안 0-based global counter (generation 경계 무관 단조 증가).
    `generation=0` = initial population, `generation>=1` = offspring 세대.
    """

    idx: int
    params: dict[str, Decimal]
    objective_value: Decimal | None  # None = degenerate
    best_so_far: Decimal | None  # cumulative best (direction 적용 후)
    is_degenerate: bool
    generation: int


@dataclass(frozen=True, slots=True)
class GeneticSearchResult:
    """Genetic 전체 결과 — iterations row-major, best_iteration_idx 직접 명시."""

    param_names: tuple[str, ...]
    iterations: tuple[GeneticIndividual, ...]
    best_params: dict[str, Decimal] | None
    best_objective_value: Decimal | None
    best_iteration_idx: int | None
    objective_metric: str
    direction: str  # Literal[maximize, minimize]
    population_size: int
    n_generations: int
    mutation_rate: Decimal
    crossover_rate: Decimal
    max_evaluations: int
    degenerate_count: int
    total_iterations: int


# === Pre-validation (Bayesian _validate_bayesian_search_pre 와 동일 패턴) ===


def _validate_genetic_search_pre(pine_source: str, param_space: ParamSpace) -> None:
    """analyze_coverage + InputDecl 부재 var_name reject + input_type 화이트리스트.

    BL-225 input_type validation (`input.int / input.float / input.string`) — Genetic 도
    CategoricalField → input.string 허용 (ordinal-style mutation 적용).
    """
    from src.strategy.pine_v2.ast_extractor import extract_content

    coverage = analyze_coverage(pine_source)
    if not coverage.is_runnable:
        unsupported = ", ".join(coverage.all_unsupported)
        raise ValueError(
            f"Strategy contains unsupported Pine built-ins: {unsupported}. "
            f"See docs/02_domain/supported-indicators.md for the supported list."
        )

    content = extract_content(pine_source)
    declared = {decl.var_name for decl in content.inputs}
    requested = set(param_space.parameters.keys())
    unknown = requested - declared
    if unknown:
        raise ValueError(
            f"param_space var_names {sorted(unknown)} are not declared as pine input variables. "
            f"Declared inputs: {sorted(declared)}."
        )

    decl_by_name: dict[str, Any] = {d.var_name: d for d in content.inputs}
    _supported_input_types = frozenset({"int", "float", "string"})
    for var_name, field in param_space.parameters.items():
        decl = decl_by_name[var_name]
        input_type = decl.input_type
        if input_type not in _supported_input_types:
            raise ValueError(
                f"Genetic search MVP does not support input.{input_type} sweep "
                f"(var_name={var_name!r}). Supported MVP: input.int, input.float, input.string."
            )
        # CategoricalField + non-string input → reject (ordinal mismatch).
        if isinstance(field, CategoricalField) and input_type != "string":
            raise ValueError(
                f"Genetic CategoricalField (var_name={var_name!r}) requires input.string. "
                f"Got input.{input_type}."
            )


# === Sampling + Selection + Crossover + Mutation ===


def _sample_individual(rng: random.Random, param_space: ParamSpace) -> dict[str, Decimal]:
    """initial population sampling — uniform random in [min, max] per variable.

    IntegerField → randint(min, max).
    DecimalField → uniform(min, max).
    CategoricalField → choice(values).
    """
    out: dict[str, Decimal] = {}
    for var_name, field in param_space.parameters.items():
        if isinstance(field, IntegerField):
            out[var_name] = Decimal(rng.randint(field.min, field.max))
        elif isinstance(field, DecimalField):
            out[var_name] = Decimal(str(rng.uniform(float(field.min), float(field.max))))
        elif isinstance(field, CategoricalField):
            out[var_name] = Decimal(str(rng.choice(field.values)))
        else:  # pragma: no cover — discriminated union exhaustive
            raise OptimizationParameterUnsupportedError(
                var_name=var_name, kind=type(field).__name__
            )
    return out


def _compare_for_selection(
    a: GeneticIndividual, b: GeneticIndividual, *, direction: str
) -> GeneticIndividual:
    """tournament 안 두 individual 비교. non-degenerate 우선 + direction 적용."""
    if a.is_degenerate and not b.is_degenerate:
        return b
    if b.is_degenerate and not a.is_degenerate:
        return a
    if a.is_degenerate and b.is_degenerate:
        return a  # 둘 다 degenerate = arbitrary (first encountered).
    assert a.objective_value is not None and b.objective_value is not None
    if direction == "maximize":
        return a if a.objective_value >= b.objective_value else b
    return a if a.objective_value <= b.objective_value else b


def _tournament_select(
    rng: random.Random,
    evaluated_pop: list[GeneticIndividual],
    *,
    direction: str,
) -> GeneticIndividual:
    """k=_TOURNAMENT_SIZE 무작위 추출 후 best 반환."""
    k = min(_TOURNAMENT_SIZE, len(evaluated_pop))
    contestants = rng.sample(evaluated_pop, k)
    best = contestants[0]
    for c in contestants[1:]:
        best = _compare_for_selection(best, c, direction=direction)
    return best


def _roulette_select(
    rng: random.Random,
    evaluated_pop: list[GeneticIndividual],
    *,
    direction: str,
) -> GeneticIndividual:
    """Rank-based roulette wheel selection. 비-degenerate 우선.

    순위 부여: best = N, worst = 1. P(i) ∝ rank(i).
    전원 degenerate인 경우 uniform random fallback (tournament와 동일 안전망).
    Sprint 57 BL-234 — ADR-013 §9.
    """
    viable = [
        ind for ind in evaluated_pop if not ind.is_degenerate and ind.objective_value is not None
    ]
    if not viable:
        return evaluated_pop[rng.randrange(len(evaluated_pop))]

    # direction-aware 정렬: maximize → 높은 값 앞 (best = index 0)
    viable.sort(key=lambda ind: ind.objective_value, reverse=(direction == "maximize"))  # type: ignore[arg-type]

    n = len(viable)
    total_rank = n * (n + 1) // 2
    threshold = rng.random() * total_rank
    cumulative: float = 0.0
    for i, ind in enumerate(viable):
        cumulative += n - i  # best(i=0) = N, worst(i=n-1) = 1
        if cumulative >= threshold:
            return ind
    return viable[-1]  # 부동소수점 오차 fallback


def _single_point_crossover(
    rng: random.Random,
    p1: dict[str, Decimal],
    p2: dict[str, Decimal],
    param_names: tuple[str, ...],
) -> dict[str, Decimal]:
    """단일 변수 list 의 1-based crossover point 무작위 자손 1개 생성.

    param_names 순서 고정 (ParamSpace.parameters insertion order). cut 이전 = p1, 이후 = p2.
    cut=0 or cut=len → 부모 한쪽 복제 회피하기 위해 [1, len-1] 범위로 제한 (len>=2 가정).
    """
    n = len(param_names)
    if n < 2:
        # 단일 변수 = crossover 불가 → p1 그대로 복제 (selection 결과 보존).
        return dict(p1)
    cut = rng.randint(1, n - 1)
    out: dict[str, Decimal] = {}
    for i, name in enumerate(param_names):
        out[name] = p1[name] if i < cut else p2[name]
    return out


def _gaussian_mutation(
    rng: random.Random,
    individual_params: dict[str, Decimal],
    *,
    mutation_rate: Decimal,
    param_space: ParamSpace,
) -> dict[str, Decimal]:
    """변수별 mutation_rate 확률로 mutate.

    IntegerField → gauss(mean=current, sigma=(max-min)*0.1) + round + clip [min, max].
    DecimalField → gauss(mean=current, sigma=(max-min)*0.1) + clip [min, max].
    CategoricalField → mutation_rate 확률로 무작위 재선택 (uniform).
    """
    mut_p = float(mutation_rate)
    out: dict[str, Decimal] = {}
    for var_name, field in param_space.parameters.items():
        current = individual_params[var_name]
        if rng.random() >= mut_p:
            out[var_name] = current
            continue
        if isinstance(field, IntegerField):
            int_span: float = float(field.max - field.min)
            int_sigma = max(1.0, int_span * float(_MUTATION_SIGMA_FRACTION))
            int_mutated = rng.gauss(mu=float(current), sigma=int_sigma)
            # banker's rounding (Python3 round) + clip.
            mutated_int = max(field.min, min(field.max, round(int_mutated)))
            out[var_name] = Decimal(mutated_int)
        elif isinstance(field, DecimalField):
            dec_span: float = float(field.max) - float(field.min)
            dec_sigma = max(1e-9, dec_span * float(_MUTATION_SIGMA_FRACTION))
            dec_mutated = rng.gauss(mu=float(current), sigma=dec_sigma)
            clipped = max(float(field.min), min(float(field.max), dec_mutated))
            out[var_name] = Decimal(str(clipped))
        elif isinstance(field, CategoricalField):
            out[var_name] = Decimal(str(rng.choice(field.values)))
        else:  # pragma: no cover
            raise OptimizationParameterUnsupportedError(
                var_name=var_name, kind=type(field).__name__
            )
    return out


# === Objective + Best tracking (Bayesian _objective_from_metrics mirror, inline) ===


def _objective_from_metrics(metrics: BacktestMetrics, *, objective_metric: str) -> Decimal | None:
    """metrics → raw objective_value. degenerate (num_trades=0 / sharpe=None) → None."""
    if metrics.num_trades == 0:
        return None
    if objective_metric == "sharpe_ratio":
        return metrics.sharpe_ratio
    if objective_metric == "total_return":
        return metrics.total_return
    if objective_metric == "max_drawdown":
        return metrics.max_drawdown
    raise OptimizationObjectiveUnsupportedError(objective_metric)


def _update_best_so_far(
    current_best: Decimal | None,
    new_value: Decimal | None,
    *,
    direction: str,
) -> Decimal | None:
    """cumulative best_so_far 갱신 (direction 적용). degenerate (None) → 무시."""
    if new_value is None:
        return current_best
    if current_best is None:
        return new_value
    if direction == "maximize":
        return max(current_best, new_value)
    return min(current_best, new_value)


def _pick_best_iteration_idx(
    iterations: tuple[GeneticIndividual, ...], *, direction: str
) -> int | None:
    """direction 적용 best iteration idx 반환. 모든 iteration degenerate → None."""
    candidates = [
        (it.idx, it.objective_value) for it in iterations if it.objective_value is not None
    ]
    if not candidates:
        return None
    if direction == "maximize":
        candidates.sort(key=lambda t: t[1], reverse=True)
    else:
        candidates.sort(key=lambda t: t[1])
    return candidates[0][0]


# === Cell config builder (Bayesian _build_cell_config 1:1 mirror) ===


def _build_cell_config(
    base: BacktestConfig | None,
    *,
    overrides: dict[str, Decimal],
) -> BacktestConfig:
    """input_overrides merge (Bayesian _build_cell_config 1:1)."""
    merged: dict[str, Any] = {}
    if base is not None and base.input_overrides is not None:
        merged.update(base.input_overrides)
    merged.update(overrides)
    if base is None:
        return BacktestConfig(input_overrides=merged)
    return dc_replace(base, input_overrides=merged)


# === Next-generation builder ===


def _create_next_generation(
    rng: random.Random,
    prev_evaluated: list[GeneticIndividual],
    *,
    mutation_rate: Decimal,
    crossover_rate: Decimal,
    direction: str,
    param_space: ParamSpace,
    param_names: tuple[str, ...],
    selection_method: Literal["tournament", "roulette"] = "tournament",
) -> list[dict[str, Decimal]]:
    """selection_method * population_size → crossover (prob) → mutation (prob).

    Sprint 57 BL-234: selection_method 파라미터 추가 (tournament | roulette).
    """
    select_fn = _roulette_select if selection_method == "roulette" else _tournament_select
    cross_p = float(crossover_rate)
    next_gen: list[dict[str, Decimal]] = []
    for _ in range(len(prev_evaluated)):
        if rng.random() < cross_p:
            p1 = select_fn(rng, prev_evaluated, direction=direction).params
            p2 = select_fn(rng, prev_evaluated, direction=direction).params
            child = _single_point_crossover(rng, p1, p2, param_names)
        else:
            child = dict(select_fn(rng, prev_evaluated, direction=direction).params)
        child = _gaussian_mutation(rng, child, mutation_rate=mutation_rate, param_space=param_space)
        next_gen.append(child)
    return next_gen


# === Main entrypoint ===


def run_genetic_search(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    param_space: ParamSpace,
    backtest_config: BacktestConfig | None = None,
) -> GeneticSearchResult:
    """ParamSpace (IntegerField + DecimalField + CategoricalField 재사용) → Genetic 실행.

    Args:
        pine_source: strategy pine 소스 (analyze_coverage pre-flight 의무).
        ohlcv: run_backtest 와 동일 shape (open/high/low/close/volume + tz-aware index).
        param_space: ParamSpace pydantic. schema_version=2 + 4 hyperparam 의무
                     (population_size / n_generations / mutation_rate / crossover_rate).
        backtest_config: None → BacktestConfig() 기본. cell override 시 input_overrides 만 변경.

    Returns:
        GeneticSearchResult — iterations row-major (idx 0..N-1), best_iteration_idx 명시.

    Raises:
        OptimizationParameterUnsupportedError (422): unknown field kind.
        OptimizationObjectiveUnsupportedError (422): objective_metric 화이트리스트 밖.
        OptimizationExecutionError (500): cell run_backtest 실패.
        ValueError: pine coverage 미통과, var_name 부재, input_type 미지원,
                    schema_version != 2, evaluation budget 초과, 4 hyperparam None.
    """
    if param_space.schema_version != 2:
        raise ValueError(
            f"Genetic search requires ParamSpace.schema_version=2 "
            f"(got {param_space.schema_version}). ADR-013 §2.2."
        )
    if param_space.objective_metric not in _SUPPORTED_OBJECTIVE_METRICS:
        raise OptimizationObjectiveUnsupportedError(param_space.objective_metric)

    if param_space.population_size is None:
        raise ValueError("Genetic search requires param_space.population_size (>= 2).")
    if param_space.n_generations is None:
        raise ValueError("Genetic search requires param_space.n_generations (>= 1).")
    if param_space.mutation_rate is None:
        raise ValueError("Genetic search requires param_space.mutation_rate ∈ (0, 1].")
    if param_space.crossover_rate is None:
        raise ValueError("Genetic search requires param_space.crossover_rate ∈ (0, 1].")

    population_size = param_space.population_size
    n_generations = param_space.n_generations
    mutation_rate = param_space.mutation_rate
    crossover_rate = param_space.crossover_rate

    budget = population_size * (n_generations + 1)
    if budget > _MAX_GENETIC_EVALUATIONS:
        raise ValueError(
            f"Genetic search evaluation budget "
            f"population_size * (n_generations + 1) = {budget} exceeds "
            f"server cap {_MAX_GENETIC_EVALUATIONS}. Reduce size/generations or split runs. "
            f"(BL-237 Sprint 57+ = dedicated queue + soft_time_limit relaxation.)"
        )
    if param_space.max_evaluations < budget:
        raise ValueError(
            f"ParamSpace.max_evaluations ({param_space.max_evaluations}) must be >= "
            f"population_size * (n_generations + 1) = {budget}."
        )

    _validate_genetic_search_pre(pine_source, param_space)

    if not param_space.parameters:
        raise ValueError("param_space.parameters must declare at least 1 variable.")

    # GA reproducibility — cryptographic strength 불필요 (search-space sampling 만).
    rng = random.Random(_GENETIC_RANDOM_STATE)  # noqa: S311
    param_names: tuple[str, ...] = tuple(param_space.parameters.keys())
    # Sprint 57 BL-234: selection_method (None → "tournament" default).
    selection_method: Literal["tournament", "roulette"] = (
        param_space.genetic_selection_method or "tournament"
    )

    iterations: list[GeneticIndividual] = []
    best_so_far: Decimal | None = None
    global_idx = 0
    prev_evaluated: list[GeneticIndividual] = []

    for gen in range(n_generations + 1):
        if gen == 0:
            pop_params = [_sample_individual(rng, param_space) for _ in range(population_size)]
        else:
            pop_params = _create_next_generation(
                rng,
                prev_evaluated,
                mutation_rate=mutation_rate,
                crossover_rate=crossover_rate,
                direction=param_space.direction,
                param_space=param_space,
                param_names=param_names,
                selection_method=selection_method,
            )

        evaluated_pop: list[GeneticIndividual] = []
        for params in pop_params:
            cfg = _build_cell_config(backtest_config, overrides=params)
            outcome = run_backtest(pine_source, ohlcv, cfg)
            if outcome.status != "ok" or outcome.result is None:
                raise OptimizationExecutionError(
                    message_public=("Backtest execution failed for one of the genetic iterations."),
                    message_internal=(
                        f"backtest failed at iteration {global_idx} "
                        f"(gen={gen}, params={params}): status={outcome.status}"
                    ),
                )
            objective_value = _objective_from_metrics(
                outcome.result.metrics, objective_metric=param_space.objective_metric
            )
            is_degenerate = objective_value is None
            best_so_far = _update_best_so_far(
                best_so_far, objective_value, direction=param_space.direction
            )
            individual = GeneticIndividual(
                idx=global_idx,
                params=params,
                objective_value=objective_value,
                best_so_far=best_so_far,
                is_degenerate=is_degenerate,
                generation=gen,
            )
            iterations.append(individual)
            evaluated_pop.append(individual)
            global_idx += 1

        prev_evaluated = evaluated_pop

    iterations_t = tuple(iterations)
    best_idx = _pick_best_iteration_idx(iterations_t, direction=param_space.direction)
    best_params: dict[str, Decimal] | None = None
    best_objective_value: Decimal | None = None
    if best_idx is not None:
        best_iter = iterations_t[best_idx]
        best_params = dict(best_iter.params)
        best_objective_value = best_iter.objective_value

    degenerate_count = sum(1 for it in iterations_t if it.is_degenerate)

    return GeneticSearchResult(
        param_names=param_names,
        iterations=iterations_t,
        best_params=best_params,
        best_objective_value=best_objective_value,
        best_iteration_idx=best_idx,
        objective_metric=param_space.objective_metric,
        direction=param_space.direction,
        population_size=population_size,
        n_generations=n_generations,
        mutation_rate=mutation_rate,
        crossover_rate=crossover_rate,
        max_evaluations=param_space.max_evaluations,
        degenerate_count=degenerate_count,
        total_iterations=len(iterations_t),
    )

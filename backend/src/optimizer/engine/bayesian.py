# Optimizer Bayesian executor — Sprint 55 ADR-013 §6 #4, scikit-optimize ask-tell loop.
"""Sprint 55 Phase 3 Optimizer Bayesian executor.

ParamSpace (BayesianHyperparamsField + IntegerField + CategoricalField) → skopt.Optimizer
ask-tell main loop → 각 iteration run_backtest → objective_metric + direction 별 best
iteration 선출 + acquisition_history.

scikit-optimize (skopt) 0.10.x 채택 = scikit-learn 1.8.0 transitive dep 이미 설치 +
ask-tell 패턴 + BSD-3 + random_state 결정성. ADR-013 §5 reference 따라 자체 ADR 신규
작성 불필요 (Sprint 55 close-out dev-log §7 amendment 1 paragraph 으로 충분).

서버 50 evaluation 강제 상한 (Plan §11.7): default queue + soft_time_limit 부재
시 cell * 50 = 250s+ Celery worker block 위험. dedicated queue + soft_time_limit
은 Sprint 56+ BL-237.

direction=maximize 처리 — skopt 는 minimization → ``-float(objective_value)`` tell
부호 반전 + best_iteration_idx 는 raw objective_value 기준 재선출 (wrapper 격리).

degenerate cell 처리 — outcome.status=="ok" but metrics.sharpe_ratio is None /
num_trades=0 → objective_value=None + ``y=_DEGENERATE_PENALTY`` (large finite, GP fit
safe). NaN/inf 는 skopt GP Cholesky decomposition fail 위험.

prior=normal — skopt 미지원 → ``NotImplementedError`` raise (Sprint 56+ 자체 sampler
wrapper). ADR-013 §7 amendment 의무.

LESSON-019 (commit-spy): 본 executor 자체는 DB 미접근. Service 가 호출 결과를
result_jsonb 로 저장 + commit. spy 회귀는 Service test 책임.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Any, Final, Literal

import pandas as pd
from skopt import Optimizer as SkoptOptimizer
from skopt.space import Categorical, Integer, Real

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.optimizer.exceptions import (
    OptimizationExecutionError,
    OptimizationObjectiveUnsupportedError,
    OptimizationParameterUnsupportedError,
)
from src.optimizer.schemas import (
    BayesianHyperparamsField,
    CategoricalField,
    DecimalField,
    IntegerField,
    ParamSpace,
)
from src.strategy.pine_v2.coverage import analyze_coverage

# Sprint 55 — Bayesian evaluation 상한. Grid Search _MAX_GRID_CELLS=9 보다 큰 상한
# (n_initial_random + acquisition iteration 수용). soft_time_limit 부재 시 worker
# block 보호. dedicated queue 는 Sprint 56+ BL-237.
_MAX_BAYESIAN_EVALUATIONS: Final[int] = 50

# Sprint 55 — degenerate cell penalty (large finite). +inf 사용 시 skopt GP Cholesky
# decomposition NaN propagation → fit fail. dynamic penalty (best+1e6) 도 가능하나
# 단순화. ADR-013 §7 amendment 명시.
_DEGENERATE_PENALTY: Final[float] = 1e10

# Sprint 55 = Bayesian 안 reproducibility 강제 — random_state 고정.
# 사용자 입력 reseed 옵션은 Sprint 56+ BL-237 묶음 검토.
_BAYESIAN_RANDOM_STATE: Final[int] = 42

# Sprint 54 MVP — BacktestMetrics 화이트리스트 (grid_search.py mirror).
_SUPPORTED_OBJECTIVE_METRICS: Final[frozenset[str]] = frozenset(
    {"sharpe_ratio", "total_return", "max_drawdown"}
)

_PRIOR_MAP: Final[dict[str, str]] = {
    # ADR-013 underscore → skopt hyphen 변환.
    "uniform": "uniform",
    "log_uniform": "log-uniform",
    # "normal" 은 skopt 미지원 — 본 모듈 안 NotImplementedError raise.
}


@dataclass(frozen=True, slots=True)
class BayesianIteration:
    """단일 Bayesian iteration 의 sample point + objective_value (direction 적용 전 raw)."""

    idx: int
    params: dict[str, Decimal]
    objective_value: Decimal | None  # None = degenerate
    best_so_far: Decimal | None  # cumulative best (direction 적용 후)
    is_degenerate: bool
    phase: Literal["random", "acquisition"]


@dataclass(frozen=True, slots=True)
class BayesianSearchResult:
    """Bayesian 전체 결과 — iterations row-major, best_iteration_idx 직접 명시."""

    param_names: tuple[str, ...]
    iterations: tuple[BayesianIteration, ...]
    best_params: dict[str, Decimal] | None
    best_objective_value: Decimal | None
    best_iteration_idx: int | None  # FE highlight (Sprint 50/51/52 retro-incorrect 차단)
    objective_metric: str
    direction: str  # Literal[maximize, minimize]
    bayesian_acquisition: str  # Literal[EI, UCB, PI]
    bayesian_n_initial_random: int
    max_evaluations: int
    degenerate_count: int
    total_iterations: int


def _param_space_to_skopt_dimensions(
    param_space: ParamSpace,
) -> tuple[list[Any], tuple[str, ...]]:
    """ParamSpace.parameters → skopt Dimension 리스트 + var_name 순서.

    BayesianHyperparamsField → Real(low, high, prior). prior=normal NotImplementedError.
    IntegerField → Integer(low, high) (uniform).
    CategoricalField → Categorical(values, transform="label") = ordinal encoding.
        ADR-013 §2.4 = Sprint 55 ordinal only; one_hot Sprint 56+ BL-234.
    DecimalField (Grid Search 잔여) → Real(min, max) uniform — Bayesian 안에서도 grid step
        무시하고 continuous sampling. (정합성: BayesianHyperparamsField 사용 권장).
    """
    dims: list[Any] = []
    names: list[str] = []
    for var_name, field in param_space.parameters.items():
        if isinstance(field, BayesianHyperparamsField):
            if field.prior == "normal":
                # Sprint 55 = 자체 sampler wrapper 미구현. Sprint 56+ ADR-013 §7 amendment.
                raise NotImplementedError(
                    f"BayesianHyperparamsField.prior='normal' 은 Sprint 55 미지원. "
                    f"prior='uniform' 또는 'log_uniform' 사용. (var_name={var_name!r}). "
                    f"Sprint 56+ BL-234 묶음 검토."
                )
            skopt_prior = _PRIOR_MAP[field.prior]
            dims.append(
                Real(
                    low=float(field.min),
                    high=float(field.max),
                    prior=skopt_prior,
                    name=var_name,
                )
            )
        elif isinstance(field, IntegerField):
            dims.append(Integer(low=field.min, high=field.max, name=var_name))
        elif isinstance(field, CategoricalField):
            dims.append(
                Categorical(categories=tuple(field.values), transform="label", name=var_name)
            )
        elif isinstance(field, DecimalField):
            # 호환성 — DecimalField 도 받기 (grid step 무시).
            dims.append(Real(low=float(field.min), high=float(field.max), name=var_name))
        else:  # pragma: no cover — discriminated union exhaustive
            raise OptimizationParameterUnsupportedError(
                var_name=var_name, kind=type(field).__name__
            )
        names.append(var_name)
    return dims, tuple(names)


def _validate_bayesian_search_pre(pine_source: str, param_space: ParamSpace) -> None:
    """pre_validate — analyze_coverage + InputDecl 부재 var_name reject (grid_search mirror).

    Sprint 54 BL-225 input_type validation 도 Bayesian 적용 (input.int/float 만 sweep).
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

    # BL-225 input_type 검증 (grid_search 패턴 mirror).
    decl_by_name: dict[str, Any] = {d.var_name: d for d in content.inputs}
    _supported_input_types = frozenset({"int", "float"})
    for var_name, field in param_space.parameters.items():
        decl = decl_by_name[var_name]
        input_type = decl.input_type
        if input_type not in _supported_input_types:
            raise ValueError(
                f"Bayesian search MVP does not support input.{input_type} sweep "
                f"(var_name={var_name!r}). Supported MVP: input.int, input.float."
            )
        # CategoricalField 는 input.string 인 경우 가능하나 Sprint 55 unsupported.
        if isinstance(field, CategoricalField) and input_type != "int":
            # ordinal encoding 으로 int 만 허용. string input 은 BL-234 Sprint 56+.
            raise ValueError(
                f"Bayesian CategoricalField (var_name={var_name!r}) MVP requires "
                f"input.int. input.string Sprint 56+ BL-234 (one_hot encoding)."
            )


def _coerce_skopt_to_decimal(values: list[Any], param_names: tuple[str, ...]) -> dict[str, Decimal]:
    """skopt ask() 결과 (list of float/int/str) → dict[var_name, Decimal].

    ADR-013 §2.3 integer rounding rule = banker's rounding (Python3 round()). int field 는
    skopt Integer 가 직접 int 반환하므로 round 불필요. float 은 Decimal(str(v)) 로 정밀도 보존.
    """
    out: dict[str, Decimal] = {}
    for name, v in zip(param_names, values, strict=True):
        if isinstance(v, int) and not isinstance(v, bool):
            out[name] = Decimal(v)
        elif isinstance(v, float):
            out[name] = Decimal(str(v))
        else:  # categorical str 등
            out[name] = Decimal(str(v))
    return out


def _build_cell_config(
    base: BacktestConfig | None,
    *,
    overrides: dict[str, Decimal],
) -> BacktestConfig:
    """grid_search.py:_build_cell_config 1:1 mirror — input_overrides merge."""
    merged: dict[str, Any] = {}
    if base is not None and base.input_overrides is not None:
        merged.update(base.input_overrides)
    merged.update(overrides)
    if base is None:
        return BacktestConfig(input_overrides=merged)
    return dc_replace(base, input_overrides=merged)


def _objective_from_metrics(metrics: Any, *, objective_metric: str) -> Decimal | None:
    """metrics → raw objective_value. degenerate (sharpe=None / num_trades=0) → None."""
    if metrics.num_trades == 0:
        return None
    if objective_metric == "sharpe_ratio":
        return metrics.sharpe_ratio  # may be None even with trades
    if objective_metric == "total_return":
        return metrics.total_return
    if objective_metric == "max_drawdown":
        return metrics.max_drawdown
    raise OptimizationObjectiveUnsupportedError(objective_metric)


def _y_from_objective(
    objective_value: Decimal | None,
    *,
    direction: str,
) -> float:
    """raw objective → skopt y (minimization). degenerate → _DEGENERATE_PENALTY."""
    if objective_value is None:
        return _DEGENERATE_PENALTY
    raw = float(objective_value)
    return -raw if direction == "maximize" else raw


def _pick_best_iteration_idx(
    iterations: tuple[BayesianIteration, ...], *, direction: str
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


def run_bayesian_search(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    param_space: ParamSpace,
    backtest_config: BacktestConfig | None = None,
) -> BayesianSearchResult:
    """ParamSpace (Sprint 55 BayesianHyperparamsField + IntegerField + CategoricalField) → Bayesian 실행.

    Args:
        pine_source: strategy pine 소스 (analyze_coverage pre-flight 필수).
        ohlcv: run_backtest 동일 shape (open/high/low/close/volume + tz-aware index).
        param_space: ParamSpace pydantic. schema_version=2 + bayesian_acquisition/bayesian_n_initial_random
                     필수. cross-field validator 가 1차 강제.
        backtest_config: None → BacktestConfig() 기본. cell override 시 input_overrides 만 변경.

    Returns:
        BayesianSearchResult — iterations row-major (idx 순서), best_iteration_idx 명시.

    Raises:
        OptimizationParameterUnsupportedError (422): unknown field kind.
        OptimizationObjectiveUnsupportedError (422): objective_metric 화이트리스트 밖.
        OptimizationExecutionError (500): cell run_backtest 실패.
        NotImplementedError: BayesianHyperparamsField.prior='normal' (Sprint 56+ BL-234).
        ValueError: pine coverage 미통과, var_name 부재, input_type 미지원,
                    schema_version != 2, max_evaluations > 50, bayesian_* None.
    """
    if param_space.schema_version != 2:
        raise ValueError(
            f"Bayesian search requires ParamSpace.schema_version=2 "
            f"(got {param_space.schema_version}). ADR-013 §2.2."
        )
    if param_space.objective_metric not in _SUPPORTED_OBJECTIVE_METRICS:
        raise OptimizationObjectiveUnsupportedError(param_space.objective_metric)
    if param_space.bayesian_n_initial_random is None:
        raise ValueError(
            "Bayesian search requires param_space.bayesian_n_initial_random (int >= 1)."
        )
    if param_space.bayesian_acquisition is None:
        raise ValueError(
            "Bayesian search requires param_space.bayesian_acquisition ∈ {'EI', 'UCB', 'PI'}."
        )
    if param_space.max_evaluations > _MAX_BAYESIAN_EVALUATIONS:
        raise ValueError(
            f"Bayesian search max_evaluations={param_space.max_evaluations} exceeds "
            f"server cap {_MAX_BAYESIAN_EVALUATIONS}. Reduce or split runs. "
            f"(BL-237 Sprint 56+ = dedicated queue + soft_time_limit relaxation.)"
        )
    if param_space.bayesian_n_initial_random > param_space.max_evaluations:
        raise ValueError(
            f"bayesian_n_initial_random ({param_space.bayesian_n_initial_random}) "
            f"must be <= max_evaluations ({param_space.max_evaluations})."
        )

    _validate_bayesian_search_pre(pine_source, param_space)

    dimensions, param_names = _param_space_to_skopt_dimensions(param_space)
    if not dimensions:
        raise ValueError("param_space.parameters must declare at least 1 variable.")

    # UCB → LCB 부호 변환 (skopt 는 minimization 전제 = LCB).
    skopt_acq = (
        "LCB" if param_space.bayesian_acquisition == "UCB" else param_space.bayesian_acquisition
    )

    optimizer = SkoptOptimizer(
        dimensions=dimensions,
        base_estimator="GP",
        acq_func=skopt_acq,
        n_initial_points=param_space.bayesian_n_initial_random,
        random_state=_BAYESIAN_RANDOM_STATE,
    )

    iterations: list[BayesianIteration] = []
    best_so_far: Decimal | None = None

    for i in range(param_space.max_evaluations):
        x = optimizer.ask()
        params_dict = _coerce_skopt_to_decimal(x, param_names)

        cfg = _build_cell_config(backtest_config, overrides=params_dict)
        outcome = run_backtest(pine_source, ohlcv, cfg)
        if outcome.status != "ok" or outcome.result is None:
            raise OptimizationExecutionError(
                message_public="Backtest execution failed for one of the bayesian iterations.",
                message_internal=(
                    f"backtest failed at iteration {i} (params={params_dict}): "
                    f"status={outcome.status}"
                ),
            )

        objective_value = _objective_from_metrics(
            outcome.result.metrics, objective_metric=param_space.objective_metric
        )
        is_degenerate = objective_value is None

        # cumulative best (direction 적용).
        if objective_value is not None:
            if best_so_far is None:
                best_so_far = objective_value
            elif param_space.direction == "maximize":
                best_so_far = max(best_so_far, objective_value)
            else:
                best_so_far = min(best_so_far, objective_value)

        phase: Literal["random", "acquisition"] = (
            "random" if i < param_space.bayesian_n_initial_random else "acquisition"
        )
        iterations.append(
            BayesianIteration(
                idx=i,
                params=params_dict,
                objective_value=objective_value,
                best_so_far=best_so_far,
                is_degenerate=is_degenerate,
                phase=phase,
            )
        )

        # tell — degenerate 도 penalty 로 tell (skopt 는 모든 iteration 의 결과 필요).
        y = _y_from_objective(objective_value, direction=param_space.direction)
        optimizer.tell(x, y)

    iterations_t = tuple(iterations)
    best_idx = _pick_best_iteration_idx(iterations_t, direction=param_space.direction)
    best_params: dict[str, Decimal] | None = None
    best_objective_value: Decimal | None = None
    if best_idx is not None:
        best_iter = iterations_t[best_idx]
        best_params = dict(best_iter.params)
        best_objective_value = best_iter.objective_value

    degenerate_count = sum(1 for it in iterations_t if it.is_degenerate)

    return BayesianSearchResult(
        param_names=param_names,
        iterations=iterations_t,
        best_params=best_params,
        best_objective_value=best_objective_value,
        best_iteration_idx=best_idx,
        objective_metric=param_space.objective_metric,
        direction=param_space.direction,
        bayesian_acquisition=param_space.bayesian_acquisition,
        bayesian_n_initial_random=param_space.bayesian_n_initial_random,
        max_evaluations=param_space.max_evaluations,
        degenerate_count=degenerate_count,
        total_iterations=len(iterations_t),
    )

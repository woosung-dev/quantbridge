# Optimizer Grid Search executor — Sprint 54 MVP, N-dim param_space → 최적 cell 선출.
"""Sprint 54 Phase 3 Optimizer Grid Search executor.

ParamSpace (IntegerField + DecimalField only — categorical 은 ADR-013 Sprint 55+)
→ dict[var_name, list[Decimal]] expansion → `run_grid_sweep` 위임 → 각 cell run_backtest →
objective_metric + direction 별 best cell 선출 + ranking.

서버 9 cell 강제 제한 (Sprint 50 codex P1#5 패턴 재사용): Sprint 55+ Bayesian/Genetic
도입 시 dedicated queue + soft_time_limit 설계 후 확장. ParamSpace.max_evaluations 는
사용자 의도 상한 (>= 1, schemas.py invariant) — 본 executor 는 max(max_evaluations,
_MAX_GRID_CELLS) 가 아닌 ``_MAX_GRID_CELLS`` 만 강제. param_space cardinality 자체가
9 초과면 grid_sweep 가 reject.

BL-084 보존: 매 cell run_backtest() 새 호출 → 새 PersistentStore + Interpreter.

ADR-011 §6/§8 정합: vectorbt 직접 사용 X. run_backtest = pine_v2 v2_adapter alias.

LESSON-019 (commit-spy): 본 executor 자체는 DB 미접근. Service 가 호출 결과를
result_jsonb 로 저장 + commit. spy 회귀는 Service test 책임.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Final

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.common.grid_sweep import GridSweepCellError, run_grid_sweep
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

_MAX_GRID_CELLS: Final[int] = 9  # Sprint 50/51/52 pattern mirror — soft_time_limit 부재 시 보호.

# Sprint 54 MVP — BacktestMetrics 화이트리스트 (Sprint 55+ 확장).
_SUPPORTED_OBJECTIVE_METRICS: Final[frozenset[str]] = frozenset(
    {"sharpe_ratio", "total_return", "max_drawdown"}
)


@dataclass(frozen=True, slots=True)
class GridSearchCell:
    """단일 param 조합의 backtest 결과 + objective_value (direction 적용 전 raw)."""

    param_values: dict[str, Decimal]
    sharpe: Decimal | None
    total_return: Decimal
    max_drawdown: Decimal
    num_trades: int
    is_degenerate: bool
    objective_value: Decimal | None  # objective_metric 의 cell raw value (sharpe=None → None).


@dataclass(frozen=True, slots=True)
class GridSearchResult:
    """전체 grid sweep 결과 + best cell index.

    `cells` = row-major flatten (itertools.product, 첫 var_name outermost).
    `param_names` 순서 보존 (param_space.parameters dict insertion order).
    `best_cell_index` = direction 적용 후 best cell. degenerate cell 은 ranking 제외
    (None 객체 score 비교 불가). 모든 cell degenerate 시 best_cell_index = None.
    """

    param_names: tuple[str, ...]
    param_values: dict[str, tuple[Decimal, ...]]
    cells: tuple[GridSearchCell, ...]
    objective_metric: str
    direction: str  # Literal[maximize, minimize] — schemas 에서 검증됨.
    best_cell_index: int | None


def _expand_integer_field(field: IntegerField) -> list[Decimal]:
    """IntegerField (min, max, step) → list[Decimal] (정수 Decimal)."""
    out: list[Decimal] = []
    cur = field.min
    while cur <= field.max:
        out.append(Decimal(cur))
        cur += field.step
    return out


def _expand_decimal_field(field: DecimalField) -> list[Decimal]:
    """DecimalField (min, max, step) → list[Decimal]."""
    out: list[Decimal] = []
    cur = field.min
    while cur <= field.max:
        out.append(cur)
        cur += field.step
    return out


def _expand_param_space(param_space: ParamSpace) -> dict[str, list[Decimal]]:
    """ParamSpace.parameters → grid_sweep param_grid dict.

    Sprint 54 MVP: IntegerField + DecimalField 만 expand. CategoricalField 는
    ``OptimizationParameterUnsupportedError`` (422) — ADR-013 Sprint 55+ Bayesian
    Genetic 진입 후 활성화.
    """
    grid: dict[str, list[Decimal]] = {}
    for var_name, field in param_space.parameters.items():
        if isinstance(field, IntegerField):
            grid[var_name] = _expand_integer_field(field)
        elif isinstance(field, DecimalField):
            grid[var_name] = _expand_decimal_field(field)
        elif isinstance(field, CategoricalField):
            raise OptimizationParameterUnsupportedError(var_name=var_name, kind="categorical")
        else:  # pragma: no cover — discriminated union exhaustive
            raise OptimizationParameterUnsupportedError(
                var_name=var_name, kind=type(field).__name__
            )
    return grid


def _validate_grid_search_pre(
    pine_source: str,
    grid: dict[str, list[Decimal]],
) -> None:
    """pre_validate hook — analyze_coverage + InputDecl 부재 var_name 검출.

    BL-220 ``_validate_param_grid_for_pine`` pattern mirror (stress_test/engine/param_stability.py).
    Sprint 54 Grid Search MVP 는 input_type별 정수 제약 등 BL-225 도 동일 적용.
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
    unknown = set(grid.keys()) - declared
    if unknown:
        raise ValueError(
            f"param_space var_names {sorted(unknown)} are not declared as pine input variables. "
            f"Declared inputs: {sorted(declared)}."
        )

    # BL-225 — input_type 별 grid value validation.
    decl_by_name: dict[str, object] = {d.var_name: d for d in content.inputs}
    _supported_input_types = frozenset({"int", "float"})
    for var_name in grid:
        decl = decl_by_name[var_name]
        input_type = decl.input_type  # type: ignore[attr-defined]
        if input_type not in _supported_input_types:
            raise ValueError(
                f"Grid Search MVP does not support input.{input_type} sweep "
                f"(var_name={var_name!r}). Supported MVP: input.int, input.float."
            )
        if input_type == "int":
            for v in grid[var_name]:
                if v != Decimal(int(v)):
                    raise ValueError(
                        f"input.int variable {var_name!r} requires integer Decimal values "
                        f"(got {v!r})."
                    )


def _build_cell_config(
    base: BacktestConfig | None,
    *,
    overrides: dict[str, Decimal],
) -> BacktestConfig:
    """BacktestConfig override — base 의 기존 input_overrides 보존 + grid key 갱신.

    Sprint 51 BL-222 fix pattern mirror: base 의 sizing 5필드 / init_cash / freq /
    fees / slippage / trading_sessions 모두 cell 마다 보존. dict(...) merge → grid
    key 덮어쓰기.
    """
    merged: dict[str, Decimal | int | bool | str] = {}
    if base is not None and base.input_overrides is not None:
        merged.update(base.input_overrides)
    merged.update(overrides)
    if base is None:
        return BacktestConfig(input_overrides=merged)
    return dc_replace(base, input_overrides=merged)


def _cell_objective_value(cell: GridSearchCell, *, objective_metric: str) -> Decimal | None:
    """cell raw metric → objective_value. degenerate cell or None metric → None."""
    if cell.is_degenerate:
        return None
    if objective_metric == "sharpe_ratio":
        return cell.sharpe
    if objective_metric == "total_return":
        return cell.total_return
    if objective_metric == "max_drawdown":
        return cell.max_drawdown
    # 도달 불가 (pre-check in run_grid_search) — defensive.
    raise OptimizationObjectiveUnsupportedError(objective_metric)


def _pick_best_cell_index(cells: tuple[GridSearchCell, ...], *, direction: str) -> int | None:
    """direction 적용 후 best cell idx 반환. 모든 cell degenerate → None."""
    candidates: list[tuple[int, Decimal]] = [
        (idx, c.objective_value) for idx, c in enumerate(cells) if c.objective_value is not None
    ]
    if not candidates:
        return None
    if direction == "maximize":
        candidates.sort(key=lambda t: t[1], reverse=True)
    else:  # minimize — schemas Literal lock
        candidates.sort(key=lambda t: t[1])
    return candidates[0][0]


def run_grid_search(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    param_space: ParamSpace,
    backtest_config: BacktestConfig | None = None,
) -> GridSearchResult:
    """ParamSpace (Sprint 54 MVP IntegerField/DecimalField only) → Grid Search 실행.

    Args:
        pine_source: strategy pine 소스 (analyze_coverage pre-flight 통과 필수).
        ohlcv: run_backtest 와 동일 shape (open/high/low/close/volume + tz-aware index).
        param_space: ParamSpace pydantic. schema_version=1 lock.
        backtest_config: None → BacktestConfig() 기본. cell override 시 input_overrides 만 변경.

    Returns:
        GridSearchResult — cells row-major, best_cell_index 포함.

    Raises:
        OptimizationParameterUnsupportedError (422): categorical / unknown field kind.
        OptimizationObjectiveUnsupportedError (422): objective_metric 화이트리스트 밖.
        OptimizationExecutionError (500): cell run_backtest 실패.
        ValueError: pine coverage 미통과, var_name 부재, input_type 미지원, grid 9 cell 초과.
    """
    if param_space.objective_metric not in _SUPPORTED_OBJECTIVE_METRICS:
        raise OptimizationObjectiveUnsupportedError(param_space.objective_metric)

    grid = _expand_param_space(param_space)
    if not grid:
        raise ValueError("param_space.parameters must declare at least 1 variable.")

    def _cell_runner(values: dict[str, Decimal]) -> GridSearchCell:
        cfg = _build_cell_config(backtest_config, overrides=dict(values))
        outcome = run_backtest(pine_source, ohlcv, cfg)
        if outcome.status != "ok" or outcome.result is None:
            raise OptimizationExecutionError(
                message_public="Backtest execution failed for one of the cells.",
                message_internal=(f"backtest failed at cell ({values}): status={outcome.status}"),
            )
        metrics = outcome.result.metrics
        num_trades = metrics.num_trades
        is_degenerate = num_trades == 0 or metrics.sharpe_ratio is None
        partial = GridSearchCell(
            param_values=dict(values),
            sharpe=metrics.sharpe_ratio,
            total_return=metrics.total_return,
            max_drawdown=metrics.max_drawdown,
            num_trades=num_trades,
            is_degenerate=is_degenerate,
            objective_value=None,  # 채워서 다시 dataclass 생성 (immutable).
        )
        obj_value = _cell_objective_value(partial, objective_metric=param_space.objective_metric)
        return dc_replace(partial, objective_value=obj_value)

    try:
        sweep = run_grid_sweep(
            param_grid=grid,
            cell_runner=_cell_runner,  # type: ignore[arg-type]
            max_cells=_MAX_GRID_CELLS,
            pre_validate=lambda g: _validate_grid_search_pre(pine_source, g),
        )
    except GridSweepCellError as exc:
        # cell_runner raise OptimizationExecutionError → GridSweepCellError 로 wrap됨.
        # __cause__ 통해 original 보존하면서 OptimizationExecutionError 다시 표면.
        original = exc.__cause__
        if isinstance(original, OptimizationExecutionError):
            raise original from exc
        raise OptimizationExecutionError(
            message_public="Grid search cell execution failed.",
            message_internal=str(exc),
        ) from exc

    cells_t = tuple(c.result for c in sweep.cells)
    best_idx = _pick_best_cell_index(cells_t, direction=param_space.direction)

    return GridSearchResult(
        param_names=sweep.param_names,
        param_values={k: tuple(vs) for k, vs in sweep.param_values.items()},
        cells=cells_t,
        objective_metric=param_space.objective_metric,
        direction=param_space.direction,
        best_cell_index=best_idx,
    )

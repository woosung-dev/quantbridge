# Optimizer 엔진 3종(grid/bayesian/genetic) 공유 헬퍼.
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Protocol

from src.backtest.engine.types import BacktestConfig, BacktestMetrics
from src.optimizer.exceptions import OptimizationObjectiveUnsupportedError


def build_cell_config(
    base: BacktestConfig | None,
    *,
    overrides: dict[str, Decimal],
) -> BacktestConfig:
    """BacktestConfig override — base 의 기존 input_overrides 보존 + cell key 갱신.

    Sprint 51 BL-222 fix pattern: base 의 sizing 5필드 / init_cash / freq / fees /
    slippage / trading_sessions 모두 cell 마다 보존. dict merge → cell key 덮어쓰기.
    LESSON-063: grid/bayesian/genetic 3-engine 의 _build_cell_config 1:1 통합.
    """
    merged: dict[str, Decimal | int | bool | str] = {}
    if base is not None and base.input_overrides is not None:
        merged.update(base.input_overrides)
    merged.update(overrides)
    if base is None:
        return BacktestConfig(input_overrides=merged)
    return dc_replace(base, input_overrides=merged)


def _objective_from_metrics(metrics: BacktestMetrics, *, objective_metric: str) -> Decimal | None:
    """metrics → raw objective_value. degenerate (num_trades=0 / sharpe=None) → None.

    LESSON-063: bayesian/genetic 1:1 통합 (sharpe_ratio / total_return / max_drawdown).
    """
    if metrics.num_trades == 0:
        return None
    if objective_metric == "sharpe_ratio":
        return metrics.sharpe_ratio  # may be None even with trades
    if objective_metric == "total_return":
        return metrics.total_return
    if objective_metric == "max_drawdown":
        return metrics.max_drawdown
    raise OptimizationObjectiveUnsupportedError(objective_metric)


class _HasIdxObjective(Protocol):
    """BayesianIteration / GeneticIndividual 공통 구조 (idx + objective_value).

    frozen dataclass(read-only) 호환 위해 property 선언 (writable attr Protocol 은 미충족).
    """

    @property
    def idx(self) -> int: ...

    @property
    def objective_value(self) -> Decimal | None: ...


def _pick_best_iteration_idx(
    iterations: Sequence[_HasIdxObjective], *, direction: str
) -> int | None:
    """direction 적용 best iteration idx 반환. 모든 iteration degenerate → None.

    LESSON-063: bayesian/genetic 통합 (iteration 타입만 달랐음 → Protocol 일반화).
    """
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

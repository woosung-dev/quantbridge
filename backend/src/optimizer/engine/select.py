# Optimizer 3종(grid/bayesian/genetic) kind별 엔진 선택 SSOT + best_params 추출.
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.optimizer.engine.bayesian import BayesianSearchResult, run_bayesian_search
from src.optimizer.engine.genetic import GeneticSearchResult, run_genetic_search
from src.optimizer.engine.grid_search import GridSearchResult, run_grid_search
from src.optimizer.exceptions import OptimizationKindUnsupportedError
from src.optimizer.models import OptimizationKind
from src.optimizer.schemas import ParamSpace

OptimizerResult = GridSearchResult | BayesianSearchResult | GeneticSearchResult


def run_optimizer_by_kind(
    kind: OptimizationKind,
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    param_space: ParamSpace,
    backtest_config: BacktestConfig | None = None,
) -> OptimizerResult:
    """kind 별 옵티마이저 엔진(순수함수) 호출 — optimizer/service + walk-forward 공유 SSOT.

    LESSON-063: WFO(walk_forward) 쪽 `match kind` 는 본 함수로 먼저 통합됐고,
    optimizer/service._execute 의 잔여 중복 `match` 는 optimizer-deepen A (2026-07-13)
    에서 흡수 — 이제 두 소비자(service + walk_forward)가 본 함수 1곳만 거친다.
    직렬화 페어링은 serializers.optimizer_result_to_jsonb 담당 (같은 deepen).

    (구 파일명 dispatch.py — submit 경로 Celery enqueue 추상화 optimizer/dispatcher.py
    와 이름 충돌로 select.py 로 rename, deepen N1.)
    """
    match kind:
        case OptimizationKind.GRID_SEARCH:
            return run_grid_search(
                pine_source, ohlcv, param_space=param_space, backtest_config=backtest_config
            )
        case OptimizationKind.BAYESIAN:
            return run_bayesian_search(
                pine_source, ohlcv, param_space=param_space, backtest_config=backtest_config
            )
        case OptimizationKind.GENETIC:
            return run_genetic_search(
                pine_source, ohlcv, param_space=param_space, backtest_config=backtest_config
            )
        case _:  # pragma: no cover — OptimizationKind StrEnum 3-member exhaustive
            raise OptimizationKindUnsupportedError(kind.value)


def best_params_of(result: OptimizerResult) -> dict[str, Decimal] | None:
    """3 엔진 결과 → best_params dict (없으면 None).

    grid = best_cell_index → cell.param_values / bayesian·genetic = `.best_params` 직접.
    """
    if isinstance(result, GridSearchResult):
        if result.best_cell_index is None:
            return None
        return dict(result.cells[result.best_cell_index].param_values)
    # Bayesian / Genetic 모두 .best_params 직접 노출.
    return None if result.best_params is None else dict(result.best_params)

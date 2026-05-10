# Cost Assumption Sensitivity — BacktestConfig fees x slippage 2D grid sweep MVP
"""Sprint 50 Cost Assumption Sensitivity engine.

명명 (codex P1#2): fees x slippage 는 PnL 단계 cost 가정 sensitivity. strategy
parameter (EMA period 등) sensitivity 와 본질이 다름. 진짜 Param Stability
(pine_v2 input override) = BL-220 / Sprint 51.

서버 9 cell 강제 제한 (codex P1#5): celery_app.py 에 soft_time_limit 미설정 +
dedicated queue 부재 → 100 cell 시 worker hang risk. Sprint 50 = 9 cell. 확장
은 BL 등재 후 dedicated queue + time limit 설계 후.

BL-084 보존: 매 cell run_backtest() 새 호출 → 새 PersistentStore + Interpreter
(Sprint 19 Resolved). 추가 검증은 test_cost_assumption_sensitivity_state_isolation
(call count + cfg isolation spy, codex P2#9).

ADR-011 §6/§8 정합: vectorbt 직접 사용 X. run_backtest = pine_v2 v2_adapter alias.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Final

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.strategy.pine_v2.coverage import analyze_coverage

# MVP 지원 sweep 필드 (Sprint 50). 확장 = BL-220 (pine input override) / Sprint 51.
_SUPPORTED_PARAM_KEYS: Final[frozenset[str]] = frozenset({"fees", "slippage"})
_MAX_GRID_CELLS: Final[int] = 9   # 서버 강제 제한 (codex P1#5)


@dataclass(frozen=True, slots=True)
class CostAssumptionCell:
    """단일 (fees, slippage) 조합의 backtest 결과."""

    param1_value: Decimal
    param2_value: Decimal
    sharpe: Decimal | None
    total_return: Decimal
    max_drawdown: Decimal
    num_trades: int
    is_degenerate: bool   # num_trades=0 또는 NaN sharpe → "—" 표시


@dataclass(frozen=True, slots=True)
class CostAssumptionResult:
    """2D grid sweep 결과. cells = row-major flatten (i*N2 + j)."""

    param1_name: str
    param2_name: str
    param1_values: list[Decimal] = field(default_factory=list)
    param2_values: list[Decimal] = field(default_factory=list)
    cells: list[CostAssumptionCell] = field(default_factory=list)


def _build_config(
    base: BacktestConfig | None,
    *,
    fees: Decimal,
    slippage: Decimal,
) -> BacktestConfig:
    """BacktestConfig override (fees/slippage 만)."""
    if base is None:
        return BacktestConfig(fees=float(fees), slippage=float(slippage))
    return dc_replace(base, fees=float(fees), slippage=float(slippage))


def run_cost_assumption_sensitivity(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    param_grid: dict[str, list[Decimal]],
    backtest_config: BacktestConfig | None = None,
) -> CostAssumptionResult:
    """BacktestConfig fees x slippage 2D grid sweep (서버 9 cell 제한).

    Args:
        pine_source: strategy pine 소스 (analyze_coverage pre-flight 통과 필수).
        ohlcv: run_backtest 와 동일 shape (open/high/low/close/volume + tz-aware index).
        param_grid: 정확히 2 key. 각 key ∈ _SUPPORTED_PARAM_KEYS. 총 cell ≤ 9.
        backtest_config: None → BacktestConfig() 기본. cell override 시 fees/slippage 만 변경.

    Returns:
        CostAssumptionResult — cells row-major flatten (param1 x param2).

    Raises:
        ValueError: grid 미준수, 9 cell 초과, 미지원 pine, cell backtest 실패.
    """
    if len(param_grid) != 2:
        raise ValueError(
            f"param_grid must have exactly 2 keys (got {len(param_grid)})"
        )
    keys = tuple(param_grid.keys())
    if not _SUPPORTED_PARAM_KEYS.issuperset(keys):
        raise ValueError(
            f"param_grid keys must be subset of {sorted(_SUPPORTED_PARAM_KEYS)} "
            f"(got {sorted(keys)}). 진짜 Param Stability (pine input override) = "
            f"BL-220 / Sprint 51."
        )
    param1_name, param2_name = keys
    param1_values = list(param_grid[param1_name])
    param2_values = list(param_grid[param2_name])
    if not param1_values or not param2_values:
        raise ValueError("param_grid values must not be empty")
    n_cells = len(param1_values) * len(param2_values)
    if n_cells > _MAX_GRID_CELLS:
        raise ValueError(
            f"grid size {n_cells} exceeds {_MAX_GRID_CELLS} cells "
            f"(Sprint 50 MVP 강제 제한 — codex P1#5; 확장 = dedicated Celery queue + time limit BL 등재 후)"
        )

    # pre-flight (전체 grid 공통). 미지원 pine 1개라도 → reject.
    coverage = analyze_coverage(pine_source)
    if not coverage.is_runnable:
        unsupported = ", ".join(coverage.all_unsupported)
        raise ValueError(
            f"Strategy contains unsupported Pine built-ins: {unsupported}. "
            f"See docs/02_domain/supported-indicators.md for the supported list."
        )

    cells: list[CostAssumptionCell] = []
    for v1 in param1_values:
        for v2 in param2_values:
            cfg = _build_config(
                backtest_config,
                fees=v1 if param1_name == "fees" else v2,
                slippage=v1 if param1_name == "slippage" else v2,
            )
            outcome = run_backtest(pine_source, ohlcv, cfg)
            if outcome.status != "ok" or outcome.result is None:
                raise ValueError(
                    f"backtest failed at cell ({param1_name}={v1}, {param2_name}={v2}): "
                    f"status={outcome.status}"
                )
            metrics = outcome.result.metrics
            num_trades = metrics.num_trades
            is_degenerate = num_trades == 0 or metrics.sharpe_ratio is None
            cells.append(
                CostAssumptionCell(
                    param1_value=v1,
                    param2_value=v2,
                    sharpe=metrics.sharpe_ratio,
                    total_return=metrics.total_return,
                    max_drawdown=metrics.max_drawdown,
                    num_trades=num_trades,
                    is_degenerate=is_degenerate,
                )
            )

    return CostAssumptionResult(
        param1_name=param1_name,
        param2_name=param2_name,
        param1_values=param1_values,
        param2_values=param2_values,
        cells=cells,
    )

# Param Stability — pine_v2 strategy input override 2D grid sweep (BL-220 Sprint 51)
"""Sprint 51 Param Stability engine.

명명: pine_v2 input override (EMA period x stop loss % 등 strategy parameter sweep).
Sprint 50 Cost Assumption Sensitivity (BacktestConfig fees x slippage = PnL 단계 cost
가정 sensitivity) 와 본질이 다름 — 이쪽이 BL-220 = "진짜" Param Stability.

서버 9 cell 강제 제한 (Sprint 50 codex P1#5 패턴 재사용): celery_app.py 에
soft_time_limit 미설정 + dedicated queue 부재 → 100 cell 시 worker hang risk.
Sprint 51 = 9 cell. 확장은 BL 등재 후 dedicated queue + time limit 설계 후.

BL-084 보존: 매 cell run_backtest() 새 호출 → 새 PersistentStore + Interpreter
(Sprint 19 Resolved). state_isolation test 가 call count + cfg isolation spy.

ADR-011 §6/§8 정합: vectorbt 직접 사용 X. run_backtest = pine_v2 v2_adapter alias.

LESSON-066 path: alembic migration `20260511_0001` 의 'PARAM_STABILITY' uppercase 가
SAEnum + StrEnum 일관성 유지 (Slice 6 Playwright e2e 풀 chain 2차 검증).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Final

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.pine_v2.coverage import analyze_coverage

_MAX_GRID_CELLS: Final[int] = 9  # 서버 강제 제한 (Sprint 50 codex P1#5 패턴 재사용)


@dataclass(frozen=True, slots=True)
class ParamStabilityCell:
    """단일 (param1, param2) 조합의 backtest 결과."""

    param1_value: Decimal
    param2_value: Decimal
    sharpe: Decimal | None
    total_return: Decimal
    max_drawdown: Decimal
    num_trades: int
    is_degenerate: bool  # num_trades=0 또는 NaN sharpe → "—" 표시


@dataclass(frozen=True, slots=True)
class ParamStabilityResult:
    """2D grid sweep 결과. cells = row-major flatten (i*N2 + j)."""

    param1_name: str
    param2_name: str
    param1_values: list[Decimal] = field(default_factory=list)
    param2_values: list[Decimal] = field(default_factory=list)
    cells: list[ParamStabilityCell] = field(default_factory=list)


def _build_config(
    base: BacktestConfig | None,
    *,
    overrides: dict[str, Decimal],
) -> BacktestConfig:
    """BacktestConfig override — base 의 기존 input_overrides 보존 + sweep key 갱신.

    codex Slice 3 review P2#1 fix: base 가 sweep 외 다른 override (e.g. useLongs)
    를 갖고 있으면 cell 마다 보존. dict(...) merge → sweep key 덮어쓰기.
    """
    merged: dict[str, Decimal | int | bool | str] = {}
    if base is not None and base.input_overrides is not None:
        merged.update(base.input_overrides)
    merged.update(overrides)
    if base is None:
        return BacktestConfig(input_overrides=merged)
    return dc_replace(base, input_overrides=merged)


def run_param_stability(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    param_grid: dict[str, list[Decimal]],
    backtest_config: BacktestConfig | None = None,
) -> ParamStabilityResult:
    """pine_v2 strategy input override 2D grid sweep (서버 9 cell 제한).

    Args:
        pine_source: strategy pine 소스 (analyze_coverage pre-flight 통과 필수).
        ohlcv: run_backtest 와 동일 shape (open/high/low/close/volume + tz-aware index).
        param_grid: 정확히 2 key. 각 key = pine InputDecl.var_name. 총 cell ≤ 9.
        backtest_config: None → BacktestConfig() 기본. cell override 시 input_overrides 만 변경.

    Returns:
        ParamStabilityResult — cells row-major flatten (param1 x param2).

    Raises:
        ValueError: grid 미준수, 9 cell 초과, 미지원 pine, var_name InputDecl 부재, cell backtest 실패.
    """
    if len(param_grid) != 2:
        raise ValueError(f"param_grid must have exactly 2 keys (got {len(param_grid)})")
    keys = tuple(param_grid.keys())
    param1_name, param2_name = keys
    param1_values = list(param_grid[param1_name])
    param2_values = list(param_grid[param2_name])
    if not param1_values or not param2_values:
        raise ValueError("param_grid values must not be empty")
    n_cells = len(param1_values) * len(param2_values)
    if n_cells > _MAX_GRID_CELLS:
        raise ValueError(
            f"grid size {n_cells} exceeds {_MAX_GRID_CELLS} cells "
            f"(Sprint 51 MVP 강제 제한; 확장 = dedicated Celery queue + time limit BL 등재 후)"
        )

    # pre-flight (전체 grid 공통). 미지원 pine 1개라도 → reject.
    coverage = analyze_coverage(pine_source)
    if not coverage.is_runnable:
        unsupported = ", ".join(coverage.all_unsupported)
        raise ValueError(
            f"Strategy contains unsupported Pine built-ins: {unsupported}. "
            f"See docs/02_domain/supported-indicators.md for the supported list."
        )

    # var_name InputDecl cross-check (codex G.0 edge case 1 — 부재 var_name 422 reject).
    content = extract_content(pine_source)
    declared_var_names = {decl.var_name for decl in content.inputs}
    grid_var_names = set(keys)
    unknown = grid_var_names - declared_var_names
    if unknown:
        raise ValueError(
            f"param_grid keys {sorted(unknown)} are not declared as pine input variables. "
            f"Declared inputs: {sorted(declared_var_names)}."
        )

    cells: list[ParamStabilityCell] = []
    for v1 in param1_values:
        for v2 in param2_values:
            cfg = _build_config(
                backtest_config,
                overrides={param1_name: v1, param2_name: v2},
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
                ParamStabilityCell(
                    param1_value=v1,
                    param2_value=v2,
                    sharpe=metrics.sharpe_ratio,
                    total_return=metrics.total_return,
                    max_drawdown=metrics.max_drawdown,
                    num_trades=num_trades,
                    is_degenerate=is_degenerate,
                )
            )

    return ParamStabilityResult(
        param1_name=param1_name,
        param2_name=param2_name,
        param1_values=param1_values,
        param2_values=param2_values,
        cells=cells,
    )

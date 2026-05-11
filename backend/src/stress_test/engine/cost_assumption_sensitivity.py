# Cost Assumption Sensitivity — BacktestConfig fees x slippage 2D grid sweep
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

Sprint 54 BL-227 lift-up: 2D nested loop 을 `src.common.grid_sweep.run_grid_sweep`
generic engine 으로 위임. _SUPPORTED_PARAM_KEYS (fees/slippage) + analyze_coverage
pre-flight + 2-key 강제 invariant 는 wrapper 안 `pre_validate` hook 로 유지
(도메인 책임). param_stability.py 의 pattern mirror.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Final, cast

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.common.grid_sweep import GridSweepCellError, run_grid_sweep
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


def _validate_param_grid_for_cost_assumption(
    pine_source: str,
    param_grid: dict[str, list[Decimal]],
) -> None:
    """pre_validate hook — cost assumption 도메인 검증 (2-key + supported key + pine coverage).

    Sprint 54 BL-227 lift-up: grid_sweep generic engine 이 책임지지 않는 도메인 검증을
    여기에 통합. param_stability `_validate_param_grid_for_pine` pattern mirror.
    """
    if len(param_grid) != 2:
        raise ValueError(
            f"param_grid must have exactly 2 keys for cost assumption sensitivity "
            f"(got {len(param_grid)}). 진짜 Param Stability (N-dim sweep) = BL-220 / Sprint 51."
        )
    keys = tuple(param_grid.keys())
    if not _SUPPORTED_PARAM_KEYS.issuperset(keys):
        raise ValueError(
            f"param_grid keys must be subset of {sorted(_SUPPORTED_PARAM_KEYS)} "
            f"(got {sorted(keys)}). 진짜 Param Stability (pine input override) = "
            f"BL-220 / Sprint 51."
        )
    coverage = analyze_coverage(pine_source)
    if not coverage.is_runnable:
        unsupported = ", ".join(coverage.all_unsupported)
        raise ValueError(
            f"Strategy contains unsupported Pine built-ins: {unsupported}. "
            f"See docs/02_domain/supported-indicators.md for the supported list."
        )


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
    # cell_runner 가 param1/param2 name 을 참조해야 하지만 grid_sweep 이 호출 시점에는
    # values_map 키 = param_grid 키. param_grid 검증 후 keys tuple 미리 잡아둔다.
    # pre_validate 가 2-key 강제 통과 → cell_runner 호출 시점 tuple[str, str] 보장.
    keys_for_cell: tuple[str, str] = cast(
        "tuple[str, str]",
        tuple(param_grid.keys()) if len(param_grid) == 2 else ("", ""),
    )

    def _cell_runner(values: dict[str, Decimal]) -> CostAssumptionCell:
        # pre_validate 이미 통과 후 호출 — keys_for_cell 가 정확히 2 element.
        param1_name, param2_name = keys_for_cell
        v1 = values[param1_name]
        v2 = values[param2_name]
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
        return CostAssumptionCell(
            param1_value=v1,
            param2_value=v2,
            sharpe=metrics.sharpe_ratio,
            total_return=metrics.total_return,
            max_drawdown=metrics.max_drawdown,
            num_trades=num_trades,
            is_degenerate=is_degenerate,
        )

    try:
        sweep = run_grid_sweep(
            param_grid=param_grid,
            cell_runner=_cell_runner,  # type: ignore[arg-type]
            max_cells=_MAX_GRID_CELLS,
            pre_validate=lambda g: _validate_param_grid_for_cost_assumption(
                pine_source, g
            ),
        )
    except GridSweepCellError as exc:
        # cell_runner 안 ValueError → GridSweepCellError(ValueError). 기존 API 호환:
        # ValueError 그대로 raise (caller 가 GridSweepCellError 인식 안 함).
        raise ValueError(str(exc)) from exc.__cause__

    # GridSweepResult → CostAssumptionResult adapter (2D wrapper invariant — BL-227).
    assert len(sweep.param_names) == 2
    param1_name, param2_name = sweep.param_names
    return CostAssumptionResult(
        param1_name=param1_name,
        param2_name=param2_name,
        param1_values=list(sweep.param_values[param1_name]),
        param2_values=list(sweep.param_values[param2_name]),
        cells=[c.result for c in sweep.cells],
    )

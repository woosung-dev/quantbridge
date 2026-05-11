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

Sprint 53 BL-220 lift-up: 2D nested loop 을 `src.common.grid_sweep.run_grid_sweep`
generic engine 으로 위임. BL-225 input_type validation + var_name cross-check +
analyze_coverage pre-flight 는 wrapper 안 `pre_validate` lambda 로 유지 (도메인 책임).
_build_config (BL-222 보존) 도 wrapper 안 cell_runner lambda 안에서 호출.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as dc_replace
from decimal import Decimal
from typing import Final

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig
from src.common.grid_sweep import (
    GridSweepCellError,
    run_grid_sweep,
)
from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.pine_v2.coverage import analyze_coverage

_MAX_GRID_CELLS: Final[int] = 9  # 서버 강제 제한 (Sprint 50 codex P1#5 패턴 재사용)

# Sprint 52 BL-225 — Param Stability MVP 지원 input_type. 그 외는 reject (확장 = BL 등재).
# input.int = 정수 Decimal 만 (Decimal("20.5") → int() = 20 잘림 방지 — heatmap mismatch 차단).
# input.float = numeric Decimal 모두 허용.
# input.bool / input.string / input.source / input.price / input.session / input.symbol /
# input.timeframe / input.color / input.time / generic = MVP unsupported, reject.
_SUPPORTED_INPUT_TYPES: Final[frozenset[str]] = frozenset({"int", "float"})


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


def _validate_param_grid_for_pine(
    pine_source: str,
    param_grid: dict[str, list[Decimal]],
) -> None:
    """pre_validate hook — pine 도메인 검증 (2-key + analyze_coverage + var_name + BL-225).

    Sprint 53 lift-up: grid_sweep generic engine 이 책임지지 않는 도메인 검증을
    여기에 통합. Sprint 54 BL-228 generic engine N-dim 화 후, 2-key 강제는 param_stability
    wrapper 책임 (heatmap result_jsonb param1_name/param2_name 컬럼 호환).
    Optimizer (Sprint 54) 는 별도 hook 작성 (N-dim 본격 사용).
    """
    if len(param_grid) != 2:
        raise ValueError(
            f"param_grid must have exactly 2 keys for param stability "
            f"(got {len(param_grid)}). Optimizer (Sprint 54+) 가 N-dim 본격 지원."
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
    grid_var_names = set(param_grid.keys())
    unknown = grid_var_names - declared_var_names
    if unknown:
        raise ValueError(
            f"param_grid keys {sorted(unknown)} are not declared as pine input variables. "
            f"Declared inputs: {sorted(declared_var_names)}."
        )

    # Sprint 52 BL-225 — InputDecl.input_type 별 grid value validation.
    decl_by_name: dict[str, object] = {d.var_name: d for d in content.inputs}
    for var_name in param_grid:
        decl = decl_by_name[var_name]
        input_type = decl.input_type  # type: ignore[attr-defined]
        if input_type not in _SUPPORTED_INPUT_TYPES:
            raise ValueError(
                f"Param Stability MVP (Sprint 52) does not support input.{input_type} sweep "
                f"(var_name={var_name!r}). Supported MVP: input.int, input.float. "
                f"Extension tracked under BL-225+."
            )
        if input_type == "int":
            # 정수 Decimal 만 허용. fractional → int() cast 잘림 방지 (heatmap mismatch).
            for v in param_grid[var_name]:
                if v != Decimal(int(v)):
                    raise ValueError(
                        f"input.int variable {var_name!r} requires integer Decimal values "
                        f"(got {v!r}). int() cast 시 잘림 → heatmap mismatch (BL-225)."
                    )


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
        ValueError: grid 미준수, 9 cell 초과, 미지원 pine, var_name InputDecl 부재.
        ValueError: cell backtest 실패 (GridSweepCellError → ValueError chain).
    """
    keys = tuple(param_grid.keys()) if len(param_grid) == 2 else ()

    def _cell_runner(values: dict[str, Decimal]) -> ParamStabilityCell:
        cfg = _build_config(backtest_config, overrides=dict(values))
        outcome = run_backtest(pine_source, ohlcv, cfg)
        if outcome.status != "ok" or outcome.result is None:
            raise ValueError(
                f"backtest failed at cell ({values}): status={outcome.status}"
            )
        metrics = outcome.result.metrics
        num_trades = metrics.num_trades
        is_degenerate = num_trades == 0 or metrics.sharpe_ratio is None
        # ParamStabilityCell API 보존 — param_values dict 에서 row-major 순서 추출
        # (grid_sweep 가 invariant 보장: dict insertion = param_grid key 순서)
        param1_name, param2_name = keys  # cell_runner 호출 시점에 keys 이미 확정
        return ParamStabilityCell(
            param1_value=values[param1_name],
            param2_value=values[param2_name],
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
            pre_validate=lambda g: _validate_param_grid_for_pine(pine_source, g),
        )
    except GridSweepCellError as exc:
        # cell_runner 안 ValueError → GridSweepCellError(ValueError). 기존 API 호환:
        # ValueError 그대로 raise (caller 가 GridSweepCellError 인식 안 함).
        # __cause__ 보존은 chain 으로 유지.
        raise ValueError(str(exc)) from exc.__cause__

    # GridSweepResult → ParamStabilityResult adapter
    assert len(sweep.param_names) == 2  # invariant (engine 2-key 강제)
    param1_name, param2_name = sweep.param_names
    return ParamStabilityResult(
        param1_name=param1_name,
        param2_name=param2_name,
        param1_values=list(sweep.param_values[param1_name]),
        param2_values=list(sweep.param_values[param2_name]),
        cells=[c.result for c in sweep.cells],
    )

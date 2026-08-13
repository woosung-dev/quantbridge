# CA/PS 공유 2D grid-sweep 결과 DTO + 셀 빌더 + adapter (BL-392 통합 — 8-site 평행정의 제거)
"""stress_test 2D grid-sweep 의 셀별 백테스트 지표 결과 공유 DTO.

Cost Assumption Sensitivity (fees x slippage) 와 Param Stability (pine input override)
는 _의미_ 는 다르나 (BL-392 over-abstraction 가드 — 엔진 fn / pre_validate / _build_config
는 분리 유지) **결과 shape 는 동일** = 7-field cell + 2D wrapper. 이전엔 engine dataclass
x2 + serializer x4 + schema x2 = 8 site 평행 정의였고, `result` 가 untyped JSONB 라
한 곳만 drift 해도 GET-detail 때 KeyError (비싼 Celery run 성공 후). 본 모듈이 그 단일 SSOT.

infra `src.common.grid_sweep.GridSweepCell`/`GridSweepResult[T]` (도메인 무관 generic 엔진)
와 이름 충돌을 피하려 `GridSweepMetrics*` 접두를 쓴다 — 이쪽은 백테스트 지표를 담는 도메인 DTO.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final

from src.common.grid_sweep import GridSweepCell, GridSweepResult

# C4 graft — grid-sweep 불변식 SSOT (이전엔 engine CA/PS + schema CA/PS 에 평행 정의).
# schema validator 가 heavy engine 체인 대신 본 light 모듈에서 import (drift 차단 + 경량 import).
MAX_GRID_CELLS: Final[int] = 9  # 서버 강제 제한 (Sprint 50 codex P1#5). dedicated queue 후 확장.
GRID_PARAM_COUNT: Final[int] = 2  # 2D heatmap (result_jsonb param1/param2 컬럼 호환) 강제.
# Cost Assumption Sensitivity 전용 sweep key (PnL 단계 cost 가정). PS 는 pine input var_name 사용.
COST_ASSUMPTION_PARAM_KEYS: Final[frozenset[str]] = frozenset({"fees", "slippage"})


@dataclass(frozen=True, slots=True)
class GridSweepMetricsCell:
    """단일 (param1, param2) 조합의 backtest 지표 결과."""

    param1_value: Decimal
    param2_value: Decimal
    sharpe: Decimal | None
    total_return: Decimal
    max_drawdown: Decimal
    num_trades: int
    is_degenerate: bool  # num_trades=0 또는 NaN sharpe → "—" 표시


@dataclass(frozen=True, slots=True)
class GridSweepMetricsResult:
    """2D grid sweep 결과. cells = row-major flatten (i*N2 + j)."""

    param1_name: str
    param2_name: str
    param1_values: list[Decimal] = field(default_factory=list)
    param2_values: list[Decimal] = field(default_factory=list)
    cells: list[GridSweepMetricsCell] = field(default_factory=list)


def metrics_cell(
    *,
    param1_value: Decimal,
    param2_value: Decimal,
    sharpe: Decimal | None,
    total_return: Decimal,
    max_drawdown: Decimal,
    num_trades: int,
) -> GridSweepMetricsCell:
    """셀 빌더 — `is_degenerate` 규칙(num_trades=0 또는 sharpe=None) 단일 정의.

    CA/PS cell_runner 가 metrics 추출 후 공통 호출 → degenerate 판정 drift 차단.
    """
    return GridSweepMetricsCell(
        param1_value=param1_value,
        param2_value=param2_value,
        sharpe=sharpe,
        total_return=total_return,
        max_drawdown=max_drawdown,
        num_trades=num_trades,
        is_degenerate=num_trades == 0 or sharpe is None,
    )


def to_metrics_result(
    sweep: GridSweepResult[GridSweepMetricsCell],
) -> GridSweepMetricsResult:
    """generic `GridSweepResult` → 도메인 `GridSweepMetricsResult` adapter (2D 강제).

    CA/PS wrapper 가 `run_grid_sweep` 결과를 동일하게 변환하던 tail 블록의 단일 정의.
    """
    assert len(sweep.param_names) == GRID_PARAM_COUNT  # engine 2-key 강제 invariant
    param1_name, param2_name = sweep.param_names
    return GridSweepMetricsResult(
        param1_name=param1_name,
        param2_name=param2_name,
        param1_values=list(sweep.param_values[param1_name]),
        param2_values=list(sweep.param_values[param2_name]),
        cells=[_cell_of(c) for c in sweep.cells],
    )


def _cell_of(cell: GridSweepCell[GridSweepMetricsCell]) -> GridSweepMetricsCell:
    return cell.result

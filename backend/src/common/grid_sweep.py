# 2 변수 그리드 sweep generic 엔진. 도메인 무관 (common/), Sprint 53+ Optimizer 재사용 path.

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Generic, TypeVar

T = TypeVar("T")


class GridSweepCellError(ValueError):
    """cell_runner 실행 실패 시 raise. raise ... from exc 로 __cause__ 보존 의무.

    codex Sprint 53 G.0 P1#2 — 원본 예외 손실 방어. cell 좌표 메시지에 명시.
    """


@dataclass(frozen=True, slots=True)
class GridSweepCell(Generic[T]):
    """단일 grid 셀 결과. param_values dict = N-dim 호환 (Sprint 53 = 2 key)."""

    param_values: Mapping[str, Decimal]
    result: T


@dataclass(frozen=True, slots=True)
class GridSweepResult(Generic[T]):
    """전체 sweep 결과. cells = row-major flatten. tuple lock — caller mutation 차단."""

    param_names: tuple[str, ...]
    param_values: Mapping[str, tuple[Decimal, ...]]
    cells: tuple[GridSweepCell[T], ...]


def run_grid_sweep(
    *,
    param_grid: dict[str, list[Decimal]],
    cell_runner: Callable[[Mapping[str, Decimal]], T],
    max_cells: int = 9,
    pre_validate: Callable[[dict[str, list[Decimal]]], None] | None = None,
) -> GridSweepResult[T]:
    """2 변수 grid sweep — row-major flatten.

    Args:
        param_grid: 정확히 2 key (Sprint 53 MVP). 각 key = 도메인 식별자 (pine InputDecl.var_name 등).
        cell_runner: cell 단위 실행 callback. `Mapping[str, Decimal]` 전체 받음 — N-dim 호환.
        max_cells: 셀 상한 (>0 의무).
        pre_validate: 도메인 검증 hook — param_grid 전체 받음 (BL-225 input_type validation 등).

    Returns:
        GridSweepResult[T] — cells row-major (param1 outer x param2 inner).

    Raises:
        ValueError: param_grid 위반 (2 key X, 빈 값 list, cell 초과), max_cells <= 0, pre_validate raise.
        GridSweepCellError: cell_runner 실패 시 raise (__cause__ = 원본 예외).
    """
    if max_cells <= 0:
        raise ValueError(f"max_cells must be positive (got {max_cells})")

    if len(param_grid) != 2:
        raise ValueError(
            f"param_grid must have exactly 2 keys (got {len(param_grid)}). "
            "Sprint 53 MVP — N-dim 확장은 BL-228."
        )

    for key, values in param_grid.items():
        if not values:
            raise ValueError(f"param_grid[{key!r}] values must not be empty")

    keys = tuple(param_grid.keys())
    param1_name, param2_name = keys
    param1_values = list(param_grid[param1_name])
    param2_values = list(param_grid[param2_name])

    n_cells = len(param1_values) * len(param2_values)
    if n_cells > max_cells:
        raise ValueError(
            f"grid cell count {n_cells} exceeds {max_cells} cells "
            f"({param1_name}={len(param1_values)} x {param2_name}={len(param2_values)})"
        )

    if pre_validate is not None:
        pre_validate(param_grid)

    cells: list[GridSweepCell[T]] = []
    for v1 in param1_values:
        for v2 in param2_values:
            values_map: Mapping[str, Decimal] = {param1_name: v1, param2_name: v2}
            try:
                result = cell_runner(values_map)
            except Exception as exc:
                raise GridSweepCellError(
                    f"cell_runner 실패 ({param1_name}={v1}, {param2_name}={v2}): {exc}"
                ) from exc
            cells.append(GridSweepCell(param_values=values_map, result=result))

    return GridSweepResult(
        param_names=keys,
        param_values={
            param1_name: tuple(param1_values),
            param2_name: tuple(param2_values),
        },
        cells=tuple(cells),
    )

# N-dim 그리드 sweep generic 엔진. 도메인 무관 (common/), Sprint 53 prereq + Sprint 54 BL-228 N-dim 확장.

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from itertools import product
from typing import Generic, TypeVar

T = TypeVar("T")


class GridSweepCellError(ValueError):
    """cell_runner 실행 실패 시 raise. raise ... from exc 로 __cause__ 보존 의무.

    codex Sprint 53 G.0 P1#2 — 원본 예외 손실 방어. cell 좌표 메시지에 명시.
    """


@dataclass(frozen=True, slots=True)
class GridSweepCell(Generic[T]):
    """단일 grid 셀 결과. param_values dict = N-dim 호환."""

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
    """N-dim grid sweep — row-major flatten (Sprint 54 BL-228).

    Args:
        param_grid: 1 key 이상. 각 key = 도메인 식별자 (pine InputDecl.var_name 등).
            Sprint 54 BL-228 = N-dim 호환. 도메인 wrapper 가 2D 강제 시 invariant 별도.
        cell_runner: cell 단위 실행 callback. `Mapping[str, Decimal]` 전체 받음.
        max_cells: 셀 상한 (>0 의무).
        pre_validate: 도메인 검증 hook — param_grid 전체 받음.

    Returns:
        GridSweepResult[T] — cells row-major (itertools.product, 첫 key outermost).

    Raises:
        ValueError: param_grid 빈 dict, 빈 value list, cell 초과, max_cells <= 0, pre_validate raise.
        GridSweepCellError: cell_runner 실패 시 raise (__cause__ = 원본 예외).
    """
    if max_cells <= 0:
        raise ValueError(f"max_cells must be positive (got {max_cells})")

    if len(param_grid) == 0:
        raise ValueError("param_grid must have at least 1 key")

    for key, values in param_grid.items():
        if not values:
            raise ValueError(f"param_grid[{key!r}] values must not be empty")

    keys = tuple(param_grid.keys())
    value_lists: list[list[Decimal]] = [list(param_grid[k]) for k in keys]

    n_cells = math.prod(len(vs) for vs in value_lists)
    if n_cells > max_cells:
        sizes = ", ".join(f"{k}={len(vs)}" for k, vs in zip(keys, value_lists, strict=True))
        raise ValueError(f"grid cell count {n_cells} exceeds {max_cells} cells ({sizes})")

    if pre_validate is not None:
        pre_validate(param_grid)

    cells: list[GridSweepCell[T]] = []
    for combo in product(*value_lists):
        values_map: Mapping[str, Decimal] = dict(zip(keys, combo, strict=True))
        try:
            result = cell_runner(values_map)
        except Exception as exc:
            coord = ", ".join(f"{k}={v}" for k, v in values_map.items())
            raise GridSweepCellError(f"cell_runner 실패 ({coord}): {exc}") from exc
        cells.append(GridSweepCell(param_values=values_map, result=result))

    return GridSweepResult(
        param_names=keys,
        param_values={k: tuple(vs) for k, vs in zip(keys, value_lists, strict=True)},
        cells=tuple(cells),
    )

# Sprint 54 BL-228 — N-dim grid_sweep 확장 회귀 테스트.

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

import pytest

from src.common.grid_sweep import (
    GridSweepCellError,
    run_grid_sweep,
)


def _identity_runner(values: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
    return dict(values)


def test_grid_sweep_3d_happy_path() -> None:
    """3 key sweep — 2x2x2 = 8 cells row-major (itertools.product)."""
    result = run_grid_sweep(
        param_grid={
            "a": [Decimal("1"), Decimal("2")],
            "b": [Decimal("10"), Decimal("20")],
            "c": [Decimal("100"), Decimal("200")],
        },
        cell_runner=_identity_runner,
        max_cells=9,
    )

    assert result.param_names == ("a", "b", "c")
    assert len(result.cells) == 8

    # row-major (itertools.product): a outer, c inner.
    # (1,10,100) (1,10,200) (1,20,100) (1,20,200) (2,10,100) ...
    expected = [
        (Decimal("1"), Decimal("10"), Decimal("100")),
        (Decimal("1"), Decimal("10"), Decimal("200")),
        (Decimal("1"), Decimal("20"), Decimal("100")),
        (Decimal("1"), Decimal("20"), Decimal("200")),
        (Decimal("2"), Decimal("10"), Decimal("100")),
        (Decimal("2"), Decimal("10"), Decimal("200")),
        (Decimal("2"), Decimal("20"), Decimal("100")),
        (Decimal("2"), Decimal("20"), Decimal("200")),
    ]
    actual = [
        (c.param_values["a"], c.param_values["b"], c.param_values["c"])
        for c in result.cells
    ]
    assert actual == expected


def test_grid_sweep_max_cells_boundary_n_dim() -> None:
    """3 key 2x2x3 = 12 > max_cells=9 → reject."""
    with pytest.raises(ValueError, match="12 exceeds 9"):
        run_grid_sweep(
            param_grid={
                "a": [Decimal("1"), Decimal("2")],
                "b": [Decimal("10"), Decimal("20")],
                "c": [Decimal("100"), Decimal("200"), Decimal("300")],
            },
            cell_runner=_identity_runner,
        )


def test_grid_sweep_4d_within_max_cells() -> None:
    """4 key sweep — 각 1 cell씩 1x1x1x1 = 1, max_cells=9 안."""
    result = run_grid_sweep(
        param_grid={
            "a": [Decimal("1")],
            "b": [Decimal("2")],
            "c": [Decimal("3")],
            "d": [Decimal("4")],
        },
        cell_runner=_identity_runner,
    )
    assert result.param_names == ("a", "b", "c", "d")
    assert len(result.cells) == 1
    cell = result.cells[0]
    assert cell.param_values == {
        "a": Decimal("1"),
        "b": Decimal("2"),
        "c": Decimal("3"),
        "d": Decimal("4"),
    }


def test_grid_sweep_cell_failure_n_dim_preserves_cause() -> None:
    """N-dim cell_runner 실패 시 __cause__ 보존 + 좌표 N개 모두 메시지."""
    original = RuntimeError("backtest engine failure: N-dim cell crash")

    def failing(values: Mapping[str, Decimal]) -> int:
        _ = values  # intentionally unused — raise immediately
        raise original

    with pytest.raises(GridSweepCellError) as exc_info:
        run_grid_sweep(
            param_grid={
                "a": [Decimal("1")],
                "b": [Decimal("2")],
                "c": [Decimal("3")],
            },
            cell_runner=failing,
        )

    assert exc_info.value.__cause__ is original
    msg = str(exc_info.value)
    assert "a=1" in msg and "b=2" in msg and "c=3" in msg


def test_grid_sweep_pre_validate_receives_full_n_dim_grid() -> None:
    """pre_validate 가 N-dim grid 전체 받음."""
    received: list[dict[str, list[Decimal]]] = []

    def validator(param_grid: dict[str, list[Decimal]]) -> None:
        received.append({k: list(v) for k, v in param_grid.items()})

    run_grid_sweep(
        param_grid={
            "emaPeriod": [Decimal("10"), Decimal("20")],
            "stopLoss": [Decimal("1.0")],
            "atrMult": [Decimal("2.0")],
        },
        cell_runner=_identity_runner,
        pre_validate=validator,
    )

    assert len(received) == 1
    assert received[0] == {
        "emaPeriod": [Decimal("10"), Decimal("20")],
        "stopLoss": [Decimal("1.0")],
        "atrMult": [Decimal("2.0")],
    }


def test_grid_sweep_n_dim_preserves_value_order() -> None:
    """sort 금지 — value list 순서 입력 그대로 (3 key version)."""
    result = run_grid_sweep(
        param_grid={
            "a": [Decimal("5"), Decimal("1")],
            "b": [Decimal("20"), Decimal("10")],
            "c": [Decimal("100")],
        },
        cell_runner=_identity_runner,
    )

    # cells row-major: a outer / b mid / c inner
    a_seq = [c.param_values["a"] for c in result.cells]
    b_seq = [c.param_values["b"] for c in result.cells]
    assert a_seq == [Decimal("5"), Decimal("5"), Decimal("1"), Decimal("1")]
    assert b_seq == [Decimal("20"), Decimal("10"), Decimal("20"), Decimal("10")]


def test_grid_sweep_n_dim_empty_value_list_rejects() -> None:
    """N-dim 에서도 빈 value list reject."""
    with pytest.raises(ValueError, match="empty"):
        run_grid_sweep(
            param_grid={
                "a": [Decimal("1")],
                "b": [],
                "c": [Decimal("3")],
            },
            cell_runner=_identity_runner,
        )

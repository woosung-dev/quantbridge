# grid_sweep generic engine 단위 테스트 (Sprint 53 BL-228 prereq).

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

import pytest

from src.common.grid_sweep import (
    GridSweepCell,
    GridSweepCellError,
    GridSweepResult,
    run_grid_sweep,
)


def _identity_runner(values: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
    """cell 마다 입력 dict 그대로 반환 — 호출 횟수 + 순서 검증용."""
    return dict(values)


def test_grid_sweep_2d_happy_path() -> None:
    """2x2 grid = 4 cells row-major."""
    result = run_grid_sweep(
        param_grid={"a": [Decimal("1"), Decimal("2")], "b": [Decimal("10"), Decimal("20")]},
        cell_runner=_identity_runner,
    )

    assert isinstance(result, GridSweepResult)
    assert result.param_names == ("a", "b")
    assert result.param_values == {"a": (Decimal("1"), Decimal("2")), "b": (Decimal("10"), Decimal("20"))}
    assert len(result.cells) == 4

    # row-major: a 가 outer (i*N2 + j) → (1,10), (1,20), (2,10), (2,20)
    expected_pairs = [
        (Decimal("1"), Decimal("10")),
        (Decimal("1"), Decimal("20")),
        (Decimal("2"), Decimal("10")),
        (Decimal("2"), Decimal("20")),
    ]
    actual_pairs = [(c.param_values["a"], c.param_values["b"]) for c in result.cells]
    assert actual_pairs == expected_pairs


def test_grid_sweep_enforces_max_cells_default_9() -> None:
    """default max_cells=9 → 10 cell (2x5) reject."""
    with pytest.raises(ValueError, match="9"):
        run_grid_sweep(
            param_grid={
                "a": [Decimal(str(i)) for i in range(2)],
                "b": [Decimal(str(i)) for i in range(5)],
            },
            cell_runner=_identity_runner,
        )


def test_grid_sweep_custom_max_cells_kwarg() -> None:
    """max_cells=4 → 5 cell (5x1) reject."""
    with pytest.raises(ValueError, match="4"):
        run_grid_sweep(
            param_grid={"a": [Decimal(str(i)) for i in range(5)], "b": [Decimal("1")]},
            cell_runner=_identity_runner,
            max_cells=4,
        )


def test_grid_sweep_rejects_zero_max_cells() -> None:
    """max_cells=0 → 모든 non-empty grid reject (codex P2)."""
    with pytest.raises(ValueError, match="max_cells"):
        run_grid_sweep(
            param_grid={"a": [Decimal("1")], "b": [Decimal("2")]},
            cell_runner=_identity_runner,
            max_cells=0,
        )


def test_grid_sweep_rejects_negative_max_cells() -> None:
    """max_cells=-1 → 명시 reject (codex P2)."""
    with pytest.raises(ValueError, match="max_cells"):
        run_grid_sweep(
            param_grid={"a": [Decimal("1")], "b": [Decimal("2")]},
            cell_runner=_identity_runner,
            max_cells=-1,
        )


def test_grid_sweep_empty_values_reject() -> None:
    """값 리스트 1개라도 빈 경우 reject."""
    with pytest.raises(ValueError, match="empty"):
        run_grid_sweep(
            param_grid={"a": [], "b": [Decimal("1")]},
            cell_runner=_identity_runner,
        )


def test_grid_sweep_rejects_empty_grid() -> None:
    """Sprint 54 BL-228 N-dim 확장 — 0 key (빈 grid) 만 reject. 1+ key 모두 허용."""
    with pytest.raises(ValueError, match="at least 1 key"):
        run_grid_sweep(
            param_grid={},
            cell_runner=_identity_runner,
        )


def test_grid_sweep_1d_single_key_allowed() -> None:
    """Sprint 54 BL-228 — 1 key sweep 허용 (single-parameter optimization edge)."""
    result = run_grid_sweep(
        param_grid={"a": [Decimal("1"), Decimal("2"), Decimal("3")]},
        cell_runner=_identity_runner,
    )
    assert result.param_names == ("a",)
    assert len(result.cells) == 3
    assert [c.param_values["a"] for c in result.cells] == [
        Decimal("1"),
        Decimal("2"),
        Decimal("3"),
    ]


def test_grid_sweep_per_cell_runner_callback() -> None:
    """runner 가 N1*N2 회 호출 — 3x2 = 6 회."""
    calls: list[Mapping[str, Decimal]] = []

    def spy(values: Mapping[str, Decimal]) -> int:
        calls.append(dict(values))
        return len(calls)

    result = run_grid_sweep(
        param_grid={
            "x": [Decimal("1"), Decimal("2"), Decimal("3")],
            "y": [Decimal("10"), Decimal("20")],
        },
        cell_runner=spy,
    )

    assert len(calls) == 6
    assert len(result.cells) == 6
    # cell result = runner 반환값 (1, 2, 3, 4, 5, 6)
    assert [c.result for c in result.cells] == [1, 2, 3, 4, 5, 6]


def test_grid_sweep_cell_failure_raises_chained() -> None:
    """runner exception → GridSweepCellError + __cause__ 보존 (codex P1)."""
    original = RuntimeError("backtest engine failure: simulation crashed")

    def failing(values: Mapping[str, Decimal]) -> int:
        raise original

    with pytest.raises(GridSweepCellError) as exc_info:
        run_grid_sweep(
            param_grid={"a": [Decimal("1")], "b": [Decimal("2")]},
            cell_runner=failing,
        )

    # raise ... from exc chaining 의무
    assert exc_info.value.__cause__ is original
    # 메시지 안에 cell 좌표 명시
    msg = str(exc_info.value)
    assert "a" in msg and "b" in msg
    assert "1" in msg and "2" in msg


def test_grid_sweep_preserves_value_order() -> None:
    """value list 순서 보존 (sort 금지)."""
    result = run_grid_sweep(
        param_grid={
            "a": [Decimal("5"), Decimal("1"), Decimal("3")],  # 의도적으로 sort 안 된 상태
            "b": [Decimal("20"), Decimal("10")],
        },
        cell_runner=_identity_runner,
    )

    # param_values 안 value list 가 입력 순서 그대로
    assert result.param_values["a"] == (Decimal("5"), Decimal("1"), Decimal("3"))
    assert result.param_values["b"] == (Decimal("20"), Decimal("10"))

    # cells 안 row-major 도 입력 순서 따름 (5,20)(5,10)(1,20)(1,10)(3,20)(3,10)
    a_seq = [c.param_values["a"] for c in result.cells]
    b_seq = [c.param_values["b"] for c in result.cells]
    assert a_seq == [Decimal("5"), Decimal("5"), Decimal("1"), Decimal("1"), Decimal("3"), Decimal("3")]
    assert b_seq == [Decimal("20"), Decimal("10"), Decimal("20"), Decimal("10"), Decimal("20"), Decimal("10")]


def test_grid_sweep_pre_validate_receives_full_grid() -> None:
    """pre_validate 가 param_grid 전체 받음 (codex P1 — key tuple X)."""
    received: list[dict[str, list[Decimal]]] = []

    def validator(param_grid: dict[str, list[Decimal]]) -> None:
        # caller 가 BL-225 input_type validation / InputDecl cross-check 등 책임 수용
        received.append({k: list(v) for k, v in param_grid.items()})

    run_grid_sweep(
        param_grid={"emaPeriod": [Decimal("10"), Decimal("20")], "stopLoss": [Decimal("1.0")]},
        cell_runner=_identity_runner,
        pre_validate=validator,
    )

    assert len(received) == 1
    assert received[0] == {
        "emaPeriod": [Decimal("10"), Decimal("20")],
        "stopLoss": [Decimal("1.0")],
    }


def test_grid_sweep_pre_validate_raise_bubbles() -> None:
    """pre_validate ValueError → cell_runner 호출 전 bubble (도메인 검증 책임)."""
    calls = 0

    def runner(values: Mapping[str, Decimal]) -> int:
        nonlocal calls
        calls += 1
        return calls

    def validator(param_grid: dict[str, list[Decimal]]) -> None:
        raise ValueError("InputDecl 'emaPeriod' input_type='source' MVP unsupported")

    with pytest.raises(ValueError, match="InputDecl"):
        run_grid_sweep(
            param_grid={"emaPeriod": [Decimal("10")], "stopLoss": [Decimal("1.0")]},
            cell_runner=runner,
            pre_validate=validator,
        )
    # cell_runner 호출 전 bubble
    assert calls == 0


def test_grid_sweep_cell_dataclass_immutable() -> None:
    """GridSweepCell 가 frozen — 외부 mutation 차단."""
    result = run_grid_sweep(
        param_grid={"a": [Decimal("1")], "b": [Decimal("2")]},
        cell_runner=_identity_runner,
    )

    cell: GridSweepCell[Mapping[str, Decimal]] = result.cells[0]
    with pytest.raises(AttributeError):
        cell.result = "mutated"  # type: ignore[misc]

    # cells 가 tuple — append 차단
    assert isinstance(result.cells, tuple)

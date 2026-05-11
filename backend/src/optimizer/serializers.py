"""Optimizer JSONB 직렬화 helpers — GridSearchResult ↔ JSONB dict.

Decimal → str, None 보존, row-major cells 보존. stress_test/serializers.py mirror.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.optimizer.engine import GridSearchCell, GridSearchResult


def grid_search_result_to_jsonb(r: GridSearchResult) -> dict[str, Any]:
    """GridSearchResult → JSONB dict. Decimal → str, cells row-major flatten."""
    return {
        "param_names": list(r.param_names),
        "param_values": {
            k: [str(v) for v in vs] for k, vs in r.param_values.items()
        },
        "cells": [
            {
                "param_values": {k: str(v) for k, v in c.param_values.items()},
                "sharpe": None if c.sharpe is None else str(c.sharpe),
                "total_return": str(c.total_return),
                "max_drawdown": str(c.max_drawdown),
                "num_trades": c.num_trades,
                "is_degenerate": c.is_degenerate,
                "objective_value": (
                    None if c.objective_value is None else str(c.objective_value)
                ),
            }
            for c in r.cells
        ],
        "objective_metric": r.objective_metric,
        "direction": r.direction,
        "best_cell_index": r.best_cell_index,
    }


def grid_search_result_from_jsonb(data: dict[str, Any]) -> GridSearchResult:
    """JSONB dict → GridSearchResult (test / detail rendering 용)."""
    param_names = tuple(data["param_names"])
    param_values: dict[str, tuple[Decimal, ...]] = {
        k: tuple(Decimal(v) for v in vs)
        for k, vs in data["param_values"].items()
    }
    cells_t = tuple(
        GridSearchCell(
            param_values={
                k: Decimal(v) for k, v in c["param_values"].items()
            },
            sharpe=None if c.get("sharpe") is None else Decimal(c["sharpe"]),
            total_return=Decimal(c["total_return"]),
            max_drawdown=Decimal(c["max_drawdown"]),
            num_trades=int(c["num_trades"]),
            is_degenerate=bool(c["is_degenerate"]),
            objective_value=(
                None if c.get("objective_value") is None
                else Decimal(c["objective_value"])
            ),
        )
        for c in data["cells"]
    )
    return GridSearchResult(
        param_names=param_names,
        param_values=param_values,
        cells=cells_t,
        objective_metric=data["objective_metric"],
        direction=data["direction"],
        best_cell_index=data.get("best_cell_index"),
    )

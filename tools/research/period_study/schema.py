"""성과와 무관하게 먼저 고정하는 연구 분모와 거래 가정."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product

TIMEFRAMES = {"1h": ("60", 60), "4h": ("240", 240), "1d": ("D", 1440)}
PATHS = ("pine", "python")
POLICIES = ("A", "B")
REENTRY_VERSION = "close_then_reenter_v1"


@dataclass(frozen=True)
class Period:
    id: str
    start: str
    end_exclusive: str


PERIODS = (
    Period("P1", "2024-01-01T00:00:00+00:00", "2024-07-01T00:00:00+00:00"),
    Period("P2", "2024-07-01T00:00:00+00:00", "2025-01-01T00:00:00+00:00"),
    Period("P3", "2025-01-01T00:00:00+00:00", "2025-07-01T00:00:00+00:00"),
    Period("P4", "2025-07-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
    Period("P5", "2026-04-24T00:00:00+00:00", "2026-10-24T00:00:00+00:00"),
)
COSTS = {"taker": "0.00020", "maker": "0.00010", "slippage": "0.00010"}


def publication_id(item: dict) -> str:
    value = item.get("publication_id", item.get("id"))
    if not isinstance(value, str) or not value or not value.isalnum():
        raise ValueError("publication_id는 비어 있지 않은 영숫자여야 합니다")
    return value


def plan(catalogue: dict, catalogue_sha256: str) -> dict:
    ids = [publication_id(item) for item in catalogue["items"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("코호트는 비어 있지 않은 고유 publication ID 목록이어야 합니다")
    cells = [
        {"publication_id": pid, "code_path": path, "policy": policy,
         "timeframe": timeframe, "period": period.id}
        for pid, path, policy, timeframe, period in product(
            ids, PATHS, POLICIES, TIMEFRAMES, PERIODS
        )
    ]
    return {
        "schema_version": 1,
        "catalogue_sha256": catalogue_sha256,
        "source_count": len(ids),
        "expected_cells": len(cells),
        "cells": cells,
        "periods": [asdict(period) for period in PERIODS],
        "timeframes": list(TIMEFRAMES),
        "code_paths": list(PATHS),
        "policies": list(POLICIES),
        "costs": COSTS,
        "cost_scenarios": ["baseline"],
        "initial_capital": "10000",
        "leverage": "1",
        "allocation_pct": "100",
        "reentry_version": REENTRY_VERSION,
        "fill_timing": "next_parent_open",
        "funding": "observed_historical_settlements",
        "period_end": "mark_open_position_without_synthetic_close",
        "selection_bias": "current_popularity_retrospective_cohort",
    }

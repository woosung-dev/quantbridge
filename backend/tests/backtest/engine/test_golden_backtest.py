"""백테스트 엔진 골든 러너 — .pine + ohlcv.csv + expected.json 스냅샷 비교."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.engine import run_backtest

GOLDEN_DIR = Path(__file__).parent / "golden"


def _discover_cases() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return [
        p
        for p in sorted(GOLDEN_DIR.iterdir())
        if p.is_dir() and (p / "strategy.pine").exists() and (p / "expected.json").exists()
    ]


@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_backtest_golden_case(case_dir: Path) -> None:
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = pd.read_csv(case_dir / "ohlcv.csv")

    out = run_backtest(src, ohlcv)

    assert out.status == expected["status"], f"status={out.status}, error={out.error}"

    if expected["status"] != "ok":
        return

    assert out.result is not None
    assert out.parse.result is not None

    actual_entries = [int(i) for i, v in enumerate(out.parse.result.entries) if bool(v)]
    actual_exits = [int(i) for i, v in enumerate(out.parse.result.exits) if bool(v)]
    assert actual_entries == expected["entries_indices"]
    assert actual_exits == expected["exits_indices"]

    exp_metrics = expected["backtest"]["metrics"]
    actual = out.result.metrics
    assert actual.num_trades == exp_metrics["num_trades"]
    for field in ("total_return", "sharpe_ratio", "max_drawdown", "win_rate"):
        assert str(getattr(actual, field)) == exp_metrics[field], (
            f"{field}: expected {exp_metrics[field]!r}, got {getattr(actual, field)!r}"
        )

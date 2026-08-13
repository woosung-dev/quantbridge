"""백테스트 엔진 골든 러너 — .pine + ohlcv.csv + expected.json 스냅샷 비교.

BL-104 (T0-pine-oco C7): pine_v2 가 `strategy.exit` 를 본격 지원하게 되어 golden case
(ema_cross_atr_sltp_v5) 가 status=ok 로 실행된다. expected.json 은 손계산 오라클
(test_golden_oracle_ema_sltp.py) 통과로 신뢰된 엔진으로 재생성됨 (anti-circular,
LESSON-039). skip 해제.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.regen_trust_layer_baseline import metrics_snapshot
from src.backtest.engine import run_backtest

GOLDEN_DIR = Path(__file__).parent / "golden"


def _discover_cases() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return [
        p
        for p in sorted(GOLDEN_DIR.iterdir())
        if p.is_dir() and (p / "strategy.pine").exists() and (p / "ohlcv.csv").exists()
    ]


@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_backtest_golden_case_smoke(case_dir: Path) -> None:
    """골든은 status·전 scalar metric·list digest·체결 봉 지점을 정확 비교한다."""
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = pd.read_csv(case_dir / "ohlcv.csv")

    out = run_backtest(src, ohlcv)

    assert out.status == expected["status"], f"status={out.status}, error={out.error}"

    if expected["status"] != "ok":
        return

    assert out.result is not None
    actual_metrics, actual_list_digests = metrics_snapshot(
        out.result.metrics,
        str,
    )
    expected_backtest = expected["backtest"]
    assert actual_metrics == expected_backtest["metrics"]
    assert actual_list_digests == expected_backtest["metrics_list_digests"]
    assert [trade.entry_bar_index for trade in out.result.trades] == expected["entries_indices"]
    assert [
        trade.exit_bar_index
        for trade in out.result.trades
        if trade.exit_bar_index is not None
    ] == expected["exits_indices"]

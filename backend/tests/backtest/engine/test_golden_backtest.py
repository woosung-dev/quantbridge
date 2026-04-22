"""백테스트 엔진 골든 러너 — .pine + ohlcv.csv + expected.json 스냅샷 비교.

pine_v2 마이그레이션 후 expected.json 은 구 엔진(vectorbt) 기준이라 비교 불가.
또한 현 golden case (ema_cross_atr_sltp_v5) 는 `strategy.exit` 를 사용하는데
pine_v2 는 아직 미지원 (Week 3+ MVP). 재생성은 `strategy.exit` 지원 추가 후
가능하므로 이 파일 전체는 skip 유지.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.engine import run_backtest

pytestmark = pytest.mark.skip(
    reason="legacy golden expectations — pine_v2 strategy.exit 지원 + expected 재생성 필요"
)

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
def test_backtest_golden_case_smoke(case_dir: Path) -> None:
    """pine_v2 smoke — status=ok + num_trades 는 정수. 구체 metric 비교는 유보."""
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = pd.read_csv(case_dir / "ohlcv.csv")

    out = run_backtest(src, ohlcv)

    assert out.status == expected["status"], f"status={out.status}, error={out.error}"

    if expected["status"] != "ok":
        return

    assert out.result is not None
    assert out.result.metrics.num_trades >= 0

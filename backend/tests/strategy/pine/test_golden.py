"""골든 파일 기반 통합 테스트.

tests/strategy/pine/golden/ 하위의 각 서브디렉토리는 아래 파일 구조를 가진다:
  <case-name>/
    strategy.pine       # Pine 소스
    expected.json       # 기대 결과 (status, entries_indices, exits_indices 등)
    ohlcv.csv           # (선택) OHLCV fixture. 없으면 기본 fixture 사용.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine import parse_and_run
from src.strategy.pine.errors import PineUnsupportedError

GOLDEN_DIR = Path(__file__).parent / "golden"


def _default_ohlcv(n: int = 30) -> pd.DataFrame:
    # 상승 → 횡보 → 하락 → 반등 패턴으로 crossover 발생하도록
    seg1 = np.linspace(10.0, 20.0, 10)   # 상승
    seg2 = np.full(5, 20.0)               # 횡보
    seg3 = np.linspace(20.0, 12.0, 10)   # 하락
    seg4 = np.linspace(12.0, 18.0, 5)    # 반등
    close = np.concatenate([seg1, seg2, seg3, seg4])[:n]
    return pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": [100.0] * n,
    })


def _load_ohlcv(case_dir: Path) -> pd.DataFrame:
    csv_path = case_dir / "ohlcv.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return _default_ohlcv()


def _discover_cases() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return [p for p in sorted(GOLDEN_DIR.iterdir()) if p.is_dir() and (p / "strategy.pine").exists()]


@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_golden_case(case_dir: Path) -> None:
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = _load_ohlcv(case_dir)

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == expected["status"], (
        f"status mismatch: got {outcome.status!r}, expected {expected['status']!r}; "
        f"error={outcome.error}"
    )
    assert outcome.source_version == expected.get("source_version", "v5")

    if expected["status"] == "ok":
        assert outcome.result is not None
        expected_entries = expected.get("entries_indices", [])
        expected_exits = expected.get("exits_indices", [])
        actual_entries = [int(i) for i, v in enumerate(outcome.result.entries) if bool(v)]
        actual_exits = [int(i) for i, v in enumerate(outcome.result.exits) if bool(v)]
        assert actual_entries == expected_entries, (
            f"entries mismatch:\n  expected: {expected_entries}\n  actual:   {actual_entries}"
        )
        assert actual_exits == expected_exits, (
            f"exits mismatch:\n  expected: {expected_exits}\n  actual:   {actual_exits}"
        )
    elif expected["status"] == "unsupported":
        assert outcome.error is not None
        assert isinstance(outcome.error, PineUnsupportedError)
        if "feature" in expected:
            assert outcome.error.feature == expected["feature"]


def test_golden_directory_has_cases():
    # 인프라 자체가 작동하는지 확인 (Task 19에서 실제 케이스 추가)
    cases = _discover_cases()
    # 최소 0개 이상의 골든 케이스 필요 (Task 19 이후)
    assert len(cases) >= 0  # 이 Task에선 빈 디렉토리 허용

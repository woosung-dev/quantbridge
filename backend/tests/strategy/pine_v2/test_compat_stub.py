"""Day 1 가드: parse_and_run_v2가 아직 NotImplementedError를 던지는지 확인.

Sprint 8b 구현 시 이 테스트는 삭제 또는 retool됨.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2 import parse_and_run_v2


def test_parse_and_run_v2_is_stub_on_day_1() -> None:
    ohlcv = pd.DataFrame({
        "open": [1.0],
        "high": [1.0],
        "low": [1.0],
        "close": [1.0],
        "volume": [1.0],
    })
    with pytest.raises(NotImplementedError, match="Tier-0 baseline only on Day 1"):
        parse_and_run_v2("// stub", ohlcv)

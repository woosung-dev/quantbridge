"""기존 `src.strategy.pine.parse_and_run` 시그니처 호환 레이어.

Sprint 8a Day 1: 인터페이스 경계만 고정. 실제 실행은 Sprint 8b+.
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine.types import ParseOutcome


def parse_and_run_v2(source: str, ohlcv: pd.DataFrame) -> ParseOutcome:
    """Tier-0 파이프라인으로 Pine Script 해석·실행. (Sprint 8b에서 구현)"""
    raise NotImplementedError(
        "pine_v2 compat layer: Tier-0 baseline only on Day 1; "
        "execution semantics land in Sprint 8b+."
    )

"""Sprint 8c — pine_v2 3-Track dispatcher.

`classify_script()` 결과에 따라:
- Track S (strategy 선언) → `run_historical()` (네이티브 strategy 실행)
- Track A (indicator + alert) → `run_virtual_strategy()` (Alert Hook + 가상 래퍼)
- Track M (indicator, alert 없음) → `run_historical()` (지표 pass-through)
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.strategy.pine_v2.ast_classifier import Track, classify_script
from src.strategy.pine_v2.event_loop import RunResult, run_historical
from src.strategy.pine_v2.virtual_strategy import VirtualRunResult, run_virtual_strategy


@dataclass(frozen=True)
class V2RunResult:
    """pine_v2 실행 결과 (3-Track 공통 반환 타입).

    - track: classify_script가 판정한 Track S/A/M/unknown.
    - historical: Track S/M일 때 run_historical 결과(RunResult).
    - virtual: Track A일 때 run_virtual_strategy 결과(VirtualRunResult).
    """

    track: Track
    historical: RunResult | None = None
    virtual: VirtualRunResult | None = None


def parse_and_run_v2(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    strict: bool = True,
) -> V2RunResult:
    """Pine 스크립트를 classify → 적절한 runner로 dispatch."""
    profile = classify_script(source)
    track = profile.track
    if track == "S":
        hist = run_historical(source, ohlcv, strict=strict)
        return V2RunResult(track=track, historical=hist)
    if track == "A":
        virt = run_virtual_strategy(source, ohlcv, strict=strict)
        return V2RunResult(track=track, virtual=virt)
    if track == "M":
        hist = run_historical(source, ohlcv, strict=strict)
        return V2RunResult(track=track, historical=hist)
    raise ValueError(
        f"parse_and_run_v2: unknown script track (declaration={profile.declaration!r})"
    )

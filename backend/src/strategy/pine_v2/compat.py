"""Sprint 8c — pine_v2 3-Track dispatcher.

`classify_script()` 결과에 따라:
- Track S (strategy 선언) → `run_historical()` (네이티브 strategy 실행)
- Track A (indicator + alert) → `run_virtual_strategy()` (Alert Hook + 가상 래퍼)
- Track M (indicator, alert 없음) → `run_historical()` (지표 pass-through)

Sprint 37 BL-185: initial_capital + Pine strategy() default_qty_type/value 를
ScriptContent 에서 추출하여 두 runner 에 전달. configure_sizing() 호출 → spot-equivalent
포지션 사이징 (3종: percent_of_equity / cash / fixed).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.strategy.pine_v2.ast_classifier import Track, classify_script
from src.strategy.pine_v2.ast_extractor import extract_content
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


def _extract_default_qty(source: str) -> tuple[str | None, float | None]:
    """Pine strategy() 의 default_qty_type/value 를 추출. strategy 가 아니면 (None, None).

    BL-185: ScriptContent.declaration 의 명시 필드 (TDD-1.1) 사용.
    """
    decl = extract_content(source).declaration
    if decl.kind != "strategy":
        return None, None
    qt = decl.default_qty_type
    qv_str = decl.default_qty_value
    qv: float | None = None
    if qv_str is not None:
        try:
            qv = float(qv_str)
        except (TypeError, ValueError):
            qv = None
    return qt, qv


def parse_and_run_v2(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    strict: bool = True,
    initial_capital: float | None = None,
) -> V2RunResult:
    """Pine 스크립트를 classify → 적절한 runner로 dispatch.

    BL-185: initial_capital 지정 시 ScriptContent 에서 default_qty_type/value 추출 후
    runner 에 전달 → StrategyState.configure_sizing 호출 → in-loop sizing 활성화.
    None 시 기존 qty=1.0 fallback (회귀 호환).
    """
    profile = classify_script(source)
    track = profile.track

    # BL-185: strategy() 만 default_qty 보유 (indicator/library/Track A indicator 는 None).
    default_qty_type: str | None = None
    default_qty_value: float | None = None
    if initial_capital is not None:
        default_qty_type, default_qty_value = _extract_default_qty(source)

    if track == "S":
        hist = run_historical(
            source, ohlcv, strict=strict,
            initial_capital=initial_capital,
            default_qty_type=default_qty_type,
            default_qty_value=default_qty_value,
        )
        return V2RunResult(track=track, historical=hist)
    if track == "A":
        virt = run_virtual_strategy(
            source, ohlcv, strict=strict,
            initial_capital=initial_capital,
            default_qty_type=default_qty_type,
            default_qty_value=default_qty_value,
        )
        return V2RunResult(track=track, virtual=virt)
    if track == "M":
        hist = run_historical(
            source, ohlcv, strict=strict,
            initial_capital=initial_capital,
            default_qty_type=default_qty_type,
            default_qty_value=default_qty_value,
        )
        return V2RunResult(track=track, historical=hist)
    raise ValueError(
        f"parse_and_run_v2: unknown script track (declaration={profile.declaration!r})"
    )

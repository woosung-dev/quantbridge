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

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.strategy.pine_v2.ast_classifier import Track, classify_script
from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.pine_v2.event_loop import RunResult
from src.strategy.pine_v2.sizing import resolve_default_qty
from src.strategy.pine_v2.virtual_strategy import VirtualRunResult


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
    initial_capital: float | None = None,
    live_position_size_pct: float | None = None,
    form_default_qty_type: str | None = None,
    form_default_qty_value: float | None = None,
    leverage: float = 1.0,
    sessions_allowed: tuple[str, ...] = (),
    input_overrides: Mapping[str, Any] | None = None,
    fill_timing: str = "bar_close",
) -> V2RunResult:
    """Pine 스크립트를 classify → 적절한 runner로 dispatch.

    BL-185: initial_capital 지정 시 ScriptContent 에서 default_qty_type/value 추출 후
    runner 에 전달 → StrategyState.configure_sizing 호출 → in-loop sizing 활성화.
    leverage 는 격리 증거금 게이트와 청산가에만 전달하며 주문 수량은 바꾸지 않는다.

    BL-188 v3 D2 priority chain (Pine > form > Live > None):
      1. Pine `strategy(default_qty_type=..., default_qty_value=...)` 명시 → override
      2. Pine 미명시 + form_default_qty_type/value 명시 → 폼 값 사용
      3. Pine·form 미명시 + live_position_size_pct 명시 → ("strategy.percent_of_equity", live_pct)
      4. 모두 None → qty=1.0 fallback (회귀 호환)
    체인의 단일 SSOT는 `sizing.resolve_default_qty`.

    sessions_allowed: tuple of session names ("asia"/"london"/"ny"). 비어있으면 24h.
    runner 가 StrategyState.sessions_allowed 에 주입 → entry placement + pending fill 양쪽
    에서 silent skip / carry-over 적용 (Live `is_allowed` 와 단일 reference 정합).
    """
    if live_position_size_pct is not None:
        assert initial_capital is not None, (
            "live_position_size_pct 명시 시 initial_capital 도 필수 — Live mirror tier "
            "는 capital baseline 없이 silent skip 금지 (BL-188 v3)."
        )

    profile = classify_script(source)
    track = profile.track

    default_qty_type, default_qty_value = resolve_default_qty(
        source,
        initial_capital=initial_capital,
        live_position_size_pct=live_position_size_pct,
        form_default_qty_type=form_default_qty_type,
        form_default_qty_value=form_default_qty_value,
    )

    # BL-201: Track S/A/M dispatch → TrackRunner registry. unknown track 은
    # TrackRunner.invoke 가 ValueError raise (compat.py:137 형식 보존).
    # classify_script() 결과 (track) 만 dispatch 단계에서 사용 — Fix #2 의무.
    from src.strategy.pine_v2.track_runner import TrackRunner

    if track not in {"S", "A", "M"}:
        # ast_classifier 가 unknown 분류 시 declaration 컨텍스트 포함 메시지 유지.
        raise ValueError(
            f"parse_and_run_v2: unknown script track (declaration={profile.declaration!r})"
        )
    # BL-104 — pyramiding cap (initial_capital 과 무관하게 추출). 미선언 시 None → cap 무효.
    pyramiding = extract_content(source).declaration.pyramiding

    return TrackRunner.invoke(
        track,
        source=source,
        ohlcv=ohlcv,
        strict=strict,
        initial_capital=initial_capital,
        default_qty_type=default_qty_type,
        default_qty_value=default_qty_value,
        leverage=leverage,
        sessions_allowed=sessions_allowed,
        input_overrides=input_overrides,
        pyramiding=pyramiding,
        # TV parity — 시장가 체결 타이밍 (기본 bar_close = 기존 byte-identical).
        fill_timing=fill_timing,
    )

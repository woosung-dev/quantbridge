"""Tier-1 가상 strategy 래퍼 — indicator + alertcondition → 자동 매매 실행.

ADR-011 §2.1.4 차별화 핵심. `collect_alerts()`가 반환한 AlertHook의
`condition_ast`를 매 bar `_eval_expr`로 재평가하여 SignalKind → strategy.*
매핑으로 자동 entry/close 호출.

v1 정책:
- LONG_ENTRY  → strategy.entry("L", long) (기존 short 자동 reverse)
- SHORT_ENTRY → strategy.entry("S", short) (기존 long 자동 reverse)
- LONG_EXIT   → strategy.close("L")
- SHORT_EXIT  → strategy.close("S")
- INFORMATION / UNKNOWN → 무시 + warning
- discrepancy=True → warning 기록 후 condition_signal 우선 (collect_alerts가 이미 반영)

H2+ 이연: trail_points / qty_percent / pyramiding / stop/limit 쌍 복합 exit (ADR-011 §13).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.strategy.pine_v2.alert_hook import SignalKind

ActionKind = Literal["entry", "close"]


@dataclass(frozen=True)
class VirtualAction:
    """SignalKind → strategy 호출로 매핑된 action."""

    kind: ActionKind
    trade_id: str
    direction: Literal["long", "short"] | None  # close에는 None


_SIGNAL_TO_ACTION: dict[SignalKind, VirtualAction] = {
    SignalKind.LONG_ENTRY: VirtualAction(kind="entry", trade_id="L", direction="long"),
    SignalKind.SHORT_ENTRY: VirtualAction(kind="entry", trade_id="S", direction="short"),
    SignalKind.LONG_EXIT: VirtualAction(kind="close", trade_id="L", direction=None),
    SignalKind.SHORT_EXIT: VirtualAction(kind="close", trade_id="S", direction=None),
}


def signal_to_action(signal: SignalKind) -> VirtualAction | None:
    """SignalKind을 VirtualAction으로 변환. 매매 신호가 아니면 None."""
    return _SIGNAL_TO_ACTION.get(signal)

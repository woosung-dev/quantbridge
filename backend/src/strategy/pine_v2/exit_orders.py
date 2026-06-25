# 백테스트 시뮬레이션과 라이브 주문 양쪽이 공유하는 exit-order 종류 + 동시-체결 우선순위 SSOT.
"""T0-pine-oco — exit-order kind + same-bar fill-priority SSOT (interface lock).

★ Wave 1 라이브-주문 워커가 이 모듈을 **import** (편집 X) 해 백테스트 sim 과
라이브 주문이 동일 enum + 동시-체결 규칙을 공유한다 → 백테스트↔라이브 정합.

- `ExitOrderKind` : TP/SL/Trailing 3종. value 는 라이브 주문이 의존하는 wire 문자열.
- `SAME_BAR_FILL_PRIORITY` : 한 bar 에서 여러 leg 가 동시 trigger 될 때 SL 우선
  (= pessimistic = 실거래 최악가정 일치). intrabar path 를 알 수 없으므로 최악을 가정.
- `fill_type_for` : cost SSOT(`_leg_cost`) 브릿지. TP=resting limit→maker,
  SL/Trail=trigger 시장체결→taker.
- `pessimistic_fill_order` : kinds 를 SAME_BAR_FILL_PRIORITY 순으로 안정 정렬.
"""
from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class ExitOrderKind(StrEnum):
    """exit-order 종류. value = 라이브 주문 wire 문자열 (변경 시 정합 깨짐)."""

    TAKE_PROFIT = "take_profit"  # resting limit → maker
    STOP_LOSS = "stop_loss"  # trigger market → taker
    TRAILING_STOP = "trailing_stop"  # ratchet trigger market → taker


# 동시 trigger 시 체결 우선순위 — SL 우선 = pessimistic. 라이브-주문도 이 순서를 공유.
SAME_BAR_FILL_PRIORITY: tuple[ExitOrderKind, ...] = (
    ExitOrderKind.STOP_LOSS,
    ExitOrderKind.TRAILING_STOP,
    ExitOrderKind.TAKE_PROFIT,
)

# 우선순위 → 정렬 키 (O(1) 조회).
_PRIORITY_RANK: dict[ExitOrderKind, int] = {
    kind: rank for rank, kind in enumerate(SAME_BAR_FILL_PRIORITY)
}


def fill_type_for(kind: ExitOrderKind) -> str:
    """cost SSOT 브릿지 — TP=maker(resting limit), SL·Trail=taker(trigger 시장체결)."""
    if kind == ExitOrderKind.TAKE_PROFIT:
        return "maker"
    return "taker"


def pessimistic_fill_order(kinds: Iterable[ExitOrderKind]) -> list[ExitOrderKind]:
    """kinds 를 SAME_BAR_FILL_PRIORITY 순으로 안정 정렬 (중복 보존)."""
    return sorted(kinds, key=lambda k: _PRIORITY_RANK[k])

"""Equity Calculator — Sprint 28 Slice 3 (BL-140b).

LiveSignal session 의 cumulative realized PnL 을 timeseries 로 누적.

영구 규칙:
- Decimal-first 합산 (Sprint 4 D8): `Decimal(str(a)) + Decimal(str(b))` (NOT `Decimal(str(a + b))`)
- JSONB 직렬화 친화적 (string 형식, frontend Decimal 호환)

PR #104 의 Activity Timeline chart placeholder (events entry/close 누적) 후속.
real value 누적 → frontend 가 dual-axis recharts 로 렌더 (Slice 3 T5).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict


class EquityPoint(TypedDict):
    """Single equity data point — JSONB-serializable."""

    timestamp_ms: int
    cumulative_pnl: str  # Decimal as string (precision 보존)


def append_equity_point(
    curve: list[EquityPoint],
    *,
    timestamp_ms: int,
    pnl_delta: Decimal,
) -> list[EquityPoint]:
    """기존 curve 에 새 datapoint 1개 append.

    Decimal 영구 규칙 (Sprint 4 D8) 정합:
    - prev cumulative = Decimal(str(curve[-1].cumulative_pnl)) (string → Decimal)
    - new cumulative = Decimal(str(prev)) + Decimal(str(pnl_delta))  ← 영구 규칙
    - return as string (JSONB 직렬화)

    P2 fix (Slice 3 self-review): 동일 timestamp_ms 두 번 들어와도 누적 (덮어쓰기 X).
    같은 ms 에 두 trade close 가능 (race). 정확성 보존.

    Args:
        curve: 기존 equity_curve (sorted by timestamp_ms ASC).
        timestamp_ms: 신규 event timestamp (UTC ms).
        pnl_delta: 신규 event 의 realized_pnl (Decimal, 음수/양수 모두 가능).

    Returns:
        신규 curve (기존 + 1 datapoint append).
    """
    last_cumulative = (
        Decimal(str(curve[-1]["cumulative_pnl"])) if curve else Decimal("0")
    )
    # ✅ Sprint 4 D8 영구 규칙 정합
    new_cumulative = last_cumulative + Decimal(str(pnl_delta))

    new_point: EquityPoint = {
        "timestamp_ms": timestamp_ms,
        "cumulative_pnl": str(new_cumulative),
    }
    return [*curve, new_point]


def recompute_equity_curve(
    closed_pnls: list[tuple[int, Decimal]],
) -> list[EquityPoint]:
    """전체 closed event 시퀀스 → equity_curve 처음부터 재계산.

    Manual recompute UI (후속 BL) + migration backfill 시 사용. 입력은
    (timestamp_ms, realized_pnl) tuple list, ASC sorted 가정.

    Args:
        closed_pnls: [(timestamp_ms, realized_pnl), ...] sorted ASC.

    Returns:
        전체 equity_curve.
    """
    curve: list[EquityPoint] = []
    for timestamp_ms, pnl in closed_pnls:
        curve = append_equity_point(curve, timestamp_ms=timestamp_ms, pnl_delta=pnl)
    return curve

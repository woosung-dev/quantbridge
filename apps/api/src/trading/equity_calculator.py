"""Equity Calculator — Sprint 28 Slice 3 (BL-140b).

LiveSignal session 의 cumulative realized PnL 을 timeseries 로 누적.

영구 규칙:
- Decimal-first 합산 (Sprint 4 D8): `Decimal(str(a)) + Decimal(str(b))` (NOT `Decimal(str(a + b))`)
- JSONB 직렬화 친화적 (string 형식, frontend Decimal 호환)

PR #104 의 Activity Timeline chart placeholder (events entry/close 누적) 후속.
real value 누적 → frontend 가 dual-axis recharts 로 렌더 (Slice 3 T5).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Literal, TypedDict

# BL-458 — `Order.realized_pnl` 의 출처. NULL `realized_pnl_synced_at` = pine_v2 추정,
# 값 있음 = 거래소 확정 `closedPnl`. FE 에 이미 출하된 판별자
# (`orders-blotter.tsx` `realizedPnlSource`)와 **같은 유니온**이라 번역 계층이 없다.
RealizedPnlSource = Literal["confirmed", "estimated"]


class EquityPoint(TypedDict):
    """Single equity data point — JSONB-serializable.

    ★이 형태는 pine 쓰기 경로가 `LiveSignalState.equity_curve` JSONB 로 **영속**하는
    구조다(`tasks/live_signal.py` → `append_equity_point`). 필수 키를 추가하면 그 쓰기
    경로가 타입 불일치가 되므로, 출처 라벨은 아래 `SessionEquityPoint` 로 분리한다.
    """

    timestamp_ms: int
    cumulative_pnl: str  # Decimal as string (precision 보존)


class SessionEquityPoint(EquityPoint):
    """읽기 시점에 출처를 얹은 커브 포인트 (BL-458).

    ★`source` 는 **그 시각에 실현된 델타**(주문 1건)의 출처이고 누적값의 출처가 아니다.
    첫 혼재 거래 이후의 누적은 구조상 혼재다. 이 기능에서 가장 오독되기 쉬운 지점이므로
    화면 문구도 이 구분을 지켜야 한다.
    """

    source: RealizedPnlSource


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


def label_curve_provenance(
    curve: Sequence[EquityPoint], sources: Sequence[RealizedPnlSource]
) -> list[SessionEquityPoint]:
    """커브 포인트에 그 시점 델타의 출처를 얹는다 (BL-458). 누적 산술에는 손대지 않는다.

    누적 규칙과 출처 라벨을 한 함수로 합치지 않는 이유 — `append_equity_point` 는 영속
    쓰기 경로가 쓰는 함수라 거기에 출처를 꿰면 스코프 밖 경로가 깨진다. 라벨은 읽기
    시점의 가산적 파생이다.

    `strict=True` 는 의도적이다. 길이가 어긋나면 **조용히 짧은 커브**가 나가는 대신
    `ValueError` 로 터진다 — 라벨이 잘못된 포인트에 붙는 것이 라벨이 없는 것보다 나쁘다.
    """
    return [{**point, "source": source} for point, source in zip(curve, sources, strict=True)]

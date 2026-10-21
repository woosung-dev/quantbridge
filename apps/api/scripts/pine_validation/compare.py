"""전체 비교창의 사건 다중집합 대조. 최신 사건 하나만 일치해도 통과시키지 않는다."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from scripts.pine_validation.models import EventInput, SignalEvent, coerce_events, utc_time


@dataclass
class SignalComparison:
    status: str
    left_count: int
    right_count: int
    missing: list[SignalEvent] = field(default_factory=list)
    extra: list[SignalEvent] = field(default_factory=list)
    opposite: list[dict[str, Any]] = field(default_factory=list)
    bar_lags: list[dict[str, Any]] = field(default_factory=list)
    metadata_differences: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "left_count": self.left_count,
            "right_count": self.right_count,
            "missing": [event.to_dict() for event in self.missing],
            "extra": [event.to_dict() for event in self.extra],
            "opposite": self.opposite,
            "bar_lags": self.bar_lags,
            "metadata_differences": self.metadata_differences,
        }


def compare_events(
    left: EventInput,
    right: EventInput,
    *,
    window_start: datetime | str | None = None,
    window_end: datetime | str | None = None,
    bar_times: Iterable[datetime] | None = None,
) -> SignalComparison:
    """왼쪽을 기준으로 누락·추가를 센다. 비교창은 [start, end)다.

    지연 짝은 진단용이다. 같은 방향의 남은 사건을 시간순으로 짝지어도 일치 판정은
    바뀌지 않는다. bar_times가 없으면 봉수를 추측하지 않고 초 차이만 낸다.
    """
    start = utc_time(window_start) if window_start is not None else None
    end = utc_time(window_end) if window_end is not None else None
    if start is not None and end is not None and start >= end:
        raise ValueError("비교창의 종료는 시작보다 뒤여야 합니다")

    def in_window(event: SignalEvent) -> bool:
        return (start is None or event.bar_time >= start) and (end is None or event.bar_time < end)

    def ordered(events: EventInput) -> list[SignalEvent]:
        return sorted(
            (event for event in coerce_events(events) if in_window(event)),
            key=lambda event: (event.bar_time, event.direction),
        )

    a, b = ordered(left), ordered(right)

    def unmatched(events: list[SignalEvent], other: list[SignalEvent]) -> list[SignalEvent]:
        counts = Counter((event.bar_time, event.direction) for event in other)
        result = []
        for event in events:
            key = (event.bar_time, event.direction)
            if counts[key]:
                counts[key] -= 1
            else:
                result.append(event)
        return result

    missing, extra = unmatched(a, b), unmatched(b, a)
    opposite_pairs = {
        "long": "short",
        "short": "long",
        "long_exit": "short_exit",
        "short_exit": "long_exit",
    }
    opposite = []
    remaining = list(extra)
    lag_missing = []
    for event in missing:
        match = next(
            (
                candidate
                for candidate in remaining
                if candidate.bar_time == event.bar_time
                and candidate.direction == opposite_pairs[event.direction]
            ),
            None,
        )
        if match is None:
            lag_missing.append(event)
        else:
            opposite.append({"left": event.to_dict(), "right": match.to_dict()})
            remaining.remove(match)

    positions = (
        {utc_time(value): i for i, value in enumerate(bar_times)} if bar_times is not None else {}
    )
    lags = []
    for direction in sorted({event.direction for event in lag_missing}):
        left_direction = [event for event in lag_missing if event.direction == direction]
        right_direction = [event for event in remaining if event.direction == direction]
        for first, second in zip(left_direction, right_direction, strict=False):
            first_index, second_index = (
                positions.get(first.bar_time),
                positions.get(second.bar_time),
            )
            lags.append(
                {
                    "left": first.to_dict(),
                    "right": second.to_dict(),
                    "lag_bars": second_index - first_index
                    if first_index is not None and second_index is not None
                    else None,
                    "lag_seconds": (second.bar_time - first.bar_time).total_seconds(),
                }
            )
    grouped_left: dict[tuple[datetime, str], list[SignalEvent]] = defaultdict(list)
    grouped_right: dict[tuple[datetime, str], list[SignalEvent]] = defaultdict(list)
    for event in a:
        grouped_left[(event.bar_time, event.direction)].append(event)
    for event in b:
        grouped_right[(event.bar_time, event.direction)].append(event)
    metadata_differences = []
    for key, first_group in grouped_left.items():
        second_group = list(grouped_right[key])
        unmatched_metadata = []
        # 같은 봉에 사건이 여럿이면 메타데이터가 같은 짝부터 소모한다. 입력 순서가
        # 달라졌다는 이유만으로 표시 오프셋 불일치를 만들지 않는다.
        for first in first_group:
            same_metadata = next(
                (
                    second
                    for second in second_group
                    if (first.confirmed_at, first.display_time)
                    == (second.confirmed_at, second.display_time)
                ),
                None,
            )
            if same_metadata is None:
                unmatched_metadata.append(first)
            else:
                second_group.remove(same_metadata)
        for first, second in zip(unmatched_metadata, second_group, strict=False):
            for field_name in ("confirmed_at", "display_time"):
                first_value, second_value = getattr(first, field_name), getattr(second, field_name)
                if first_value != second_value:
                    metadata_differences.append(
                        {
                            "bar_time": first.bar_time.isoformat(),
                            "direction": first.direction,
                            "field": field_name,
                            "left": first_value.isoformat() if first_value is not None else None,
                            "right": second_value.isoformat() if second_value is not None else None,
                            "reason": "metadata_missing"
                            if first_value is None or second_value is None
                            else "metadata_mismatch",
                        }
                    )
    status = (
        "no_signal"
        if not a and not b
        else "mismatch"
        if missing or extra or metadata_differences
        else "exact_match"
    )
    return SignalComparison(
        status, len(a), len(b), missing, extra, opposite, lags, metadata_differences
    )

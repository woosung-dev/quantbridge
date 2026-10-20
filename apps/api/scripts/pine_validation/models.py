"""로컬 Pine 검증용 사건 계약. 앱·DB 모델과 독립적이다."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

Direction = Literal["long", "short", "long_exit", "short_exit"]
_DIRECTIONS = {"long", "short", "long_exit", "short_exit"}


def utc_time(value: datetime | str) -> datetime:
    """오프셋 없는 시각을 추측하지 않고 UTC로 정규화한다."""
    result = (
        datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    )
    if not isinstance(result, datetime) or result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("사건 시각에는 UTC 또는 명시적 시간대 오프셋이 필요합니다")
    return result.astimezone(UTC)


@dataclass(frozen=True)
class SignalEvent:
    """bar_time은 조건을 평가한 봉, display_time은 차트에 표시한 봉이다."""

    bar_time: datetime
    direction: Direction
    confirmed_at: datetime | None = None
    display_time: datetime | None = None
    source_line: int | None = None

    def __post_init__(self) -> None:
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"알 수 없는 신호 방향: {self.direction}")
        object.__setattr__(self, "bar_time", utc_time(self.bar_time))
        for field_name in ("confirmed_at", "display_time"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, utc_time(value))
        if self.confirmed_at is not None and self.confirmed_at < self.bar_time:
            raise ValueError("신호 확정 시각은 사건 봉보다 앞설 수 없습니다")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SignalEvent:
        def optional_time(key: str) -> datetime | None:
            raw = value.get(key)
            return None if raw is None else utc_time(raw)

        return cls(
            bar_time=utc_time(value["bar_time"]),
            direction=cast(Direction, value["direction"]),
            confirmed_at=optional_time("confirmed_at"),
            display_time=optional_time("display_time"),
            source_line=value.get("source_line"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bar_time": self.bar_time.isoformat(),
            "direction": self.direction,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "display_time": self.display_time.isoformat() if self.display_time else None,
            "source_line": self.source_line,
        }


EventInput = Iterable[SignalEvent | Mapping[str, Any]] | Mapping[str, Any] | str


def coerce_events(value: EventInput) -> list[SignalEvent]:
    """정적 모듈 결과·JSON 배열·events 봉투를 같은 사건 목록으로 읽는다."""
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, Mapping):
        value = [value] if "direction" in value else value["events"]
    return [
        event if isinstance(event, SignalEvent) else SignalEvent.from_dict(event) for event in value
    ]

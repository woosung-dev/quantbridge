"""신뢰된 원시 봉의 확정 시점만 정렬한다. 전략·지표 계산은 하지 않는다."""

from __future__ import annotations

import csv
import gzip
import re
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def instant(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("시간대 없는 봉 시각")
    return result.astimezone(UTC)


def canonical_timeframe(value: str, chart: str | None = None) -> str:
    if value == "":
        if chart is None:
            raise ValueError("빈 시간봉에는 chart 문맥이 필요합니다")
        return canonical_timeframe(chart)
    if value in {"D", "W", "M"}:
        return "1" + value
    if re.fullmatch(r"[1-9][0-9]*", value):
        if int(value) > 1440:
            raise ValueError("분 시간봉 범위 초과")
        return value
    if re.fullmatch(r"[1-9][0-9]*[DWM]", value):
        limit = {"D": 365, "W": 52, "M": 12}[value[-1]]
        if int(value[:-1]) <= limit:
            return value
    raise ValueError("지원하지 않는 시간봉 형식: " + value)


def end_time(start: datetime, timeframe: str) -> datetime:
    value = canonical_timeframe(timeframe)
    if value.isdigit():
        return start + timedelta(minutes=int(value))
    amount, unit = int(value[:-1]), value[-1]
    if unit in {"D", "W"}:
        return start + timedelta(days=amount * (7 if unit == "W" else 1))
    month = start.year * 12 + start.month - 1 + amount
    # 월봉은 거래소가 관측한 월 시작 시각으로만 사용한다.
    if start.day != 1:
        raise ValueError("월봉 시작이 월초가 아닙니다")
    return start.replace(year=month // 12, month=month % 12 + 1)


def csv_rows(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as stream:
        yield from csv.DictReader(stream)


class FeedCursor:
    """한 번만 전진하는 원시 피드. 확정 전 H/L/C/V는 전송 객체에 넣지 않는다."""

    def __init__(self, rows, timeframe: str, *, initial_closed_limit: int = 1000):
        if type(initial_closed_limit) is not int or initial_closed_limit < 1:
            raise ValueError("원격 초기 이력 한도 오류")
        self.timeframe = canonical_timeframe(timeframe)
        self._rows = iter(rows)
        self._next = next(self._rows, None)
        self._previous_start = None
        self._previous_parent_end = None
        self._initial_limit = initial_closed_limit

    def advance(self, parent_start: datetime, parent_end: datetime, *, include_preceding: bool = True) -> dict[str, Any]:
        if parent_end <= parent_start:
            raise ValueError("부모 봉 시각 역전")
        if self._previous_parent_end is not None and parent_start < self._previous_parent_end:
            raise ValueError("부모 봉 중복·역전")
        first = self._previous_parent_end is None
        seed = deque(maxlen=self._initial_limit)
        closed = []
        intrabars, current = [], None
        while self._next is not None:
            row = self._next
            start = instant(row["timestamp"])
            end = end_time(start, self.timeframe)
            if start <= parent_start < end:
                current = {"timestamp": start.isoformat(), "end_timestamp": end.isoformat(),
                           "open": row["open"]}
            if end > parent_end:
                break
            if self._previous_start is not None and start <= self._previous_start:
                raise ValueError("원격 봉 중복·역전")
            self._previous_start = start
            complete = {key: row[key] for key in ("timestamp", "open", "high", "low", "close", "volume")}
            complete["end_timestamp"] = end.isoformat()
            if include_preceding or start >= parent_start:
                if first and end <= parent_start:
                    seed.append(complete)
                else:
                    closed.append(complete)
            if start >= parent_start:
                intrabars.append(complete)
            self._next = next(self._rows, None)
        self._previous_parent_end = parent_end
        return {"timeframe": self.timeframe, "new_closed": list(seed) + closed,
                "intrabars": intrabars, "current": current,
                "initial_seed": first, "initial_closed_limit": self._initial_limit}


class CausalFeeds:
    def __init__(self, chart_timeframe: str, cursors: dict[str, FeedCursor]):
        self.chart = canonical_timeframe(chart_timeframe)
        self.cursors = cursors

    def for_bar(self, bar: dict) -> dict:
        start = instant(bar["timestamp"])
        end = end_time(start, self.chart)
        return {"contract": "same_btc_causal_raw_v1", "chart_timeframe": self.chart,
                "parent_start": start.isoformat(), "parent_end": end.isoformat(),
                "feeds": {key: cursor.advance(start, end, include_preceding=cursor.timeframe != self.chart)
                          for key, cursor in self.cursors.items()}}

"""전략 작성용 타입. pandas/numpy 는 고정 실행 이미지에서 import 할 수 있다."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


class Bar(TypedDict):
    index: int
    timestamp: str
    open: str
    high: str
    low: str
    close: str
    volume: str


class Position(TypedDict):
    size: str
    direction: Literal["flat", "long", "short"]
    average_price: str | None


class Context(TypedDict):
    bar: Bar
    history: list[Bar]
    position: Position
    params: dict[str, Any]


class Intent(TypedDict):
    action: Literal["hold", "long", "short", "close"]
    stop_loss: NotRequired[str]
    take_profit: NotRequired[str]

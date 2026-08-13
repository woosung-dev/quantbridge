"""페이지네이션 응답 스키마 — `Page[T]` 제네릭 (items/total/limit/offset)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

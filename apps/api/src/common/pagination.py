"""페이지네이션 응답 스키마 — `Page[T]` 제네릭 (items/total/limit/offset)."""

from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int

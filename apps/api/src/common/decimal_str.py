"""Decimal → str 직렬화 타입.

응답 스키마의 Decimal 필드는 JSON 숫자(float) 정밀도 손실을 피하려고 str 로 낸다.
`@field_serializer` 를 모델마다 복제하던 것을 필드 타입으로 모은다.

- `when_used` 기본값(`always`) — python 모드 `model_dump()` 도 str 을 낸다(기존 동작 유지).
  python 모드에서 Decimal 을 그대로 내던 `when_used="json"` serializer 는 이 타입으로 옮기지 않았다.
- `return_type` 이 OpenAPI serialization 스키마(`string` / `string | null`)를 정한다.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def _to_str(v: Decimal) -> str:
    return str(v)


def _to_str_or_none(v: Decimal | None) -> str | None:
    return None if v is None else str(v)


DecimalStr = Annotated[Decimal, PlainSerializer(_to_str, return_type=str)]
DecimalStrOrNone = Annotated[
    Decimal | None, PlainSerializer(_to_str_or_none, return_type=str | None)
]

"""Custom SQLAlchemy types — naive datetime을 ORM 레이어에서 거부."""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class AwareDateTime(TypeDecorator[datetime]):
    """tz-aware datetime만 허용. naive 입력 시 즉시 ValueError.

    PostgreSQL TIMESTAMPTZ로 매핑. asyncpg가 자동으로 tz-aware datetime 반환.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: Any, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        if value.tzinfo is None:
            raise ValueError(
                f"Naive datetime rejected: {value}. "
                "Use datetime.now(UTC) or attach tzinfo."
            )
        return value

"""strategy 도메인 SQLModel 테이블. Sprint 3에서 Strategy 추가."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, SQLModel


def _utcnow() -> datetime:
    # [임시 workaround — S3-05 follow-up]
    # 정석: 컬럼을 DateTime(timezone=True) (TIMESTAMPTZ)로 정의 + datetime.now(UTC) (tz-aware) 반환.
    # 현재: migration이 sa.DateTime() (naive)으로 생성됐고 asyncpg가 tz-aware를 거부 → naive UTC 반환.
    # TimescaleDB hypertable 도입 시점(Sprint 5+) 전에 docs/TODO.md S3-05로 복구 예정.
    return datetime.now(UTC).replace(tzinfo=None)


class ParseStatus(StrEnum):
    ok = "ok"
    unsupported = "unsupported"
    error = "error"


class PineVersion(StrEnum):
    v4 = "v4"
    v5 = "v5"


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"
    __table_args__ = (
        Index(
            "ix_strategies_owner_active_updated",
            "user_id",
            "is_archived",
            "updated_at",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("users.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    name: str = Field(max_length=120, nullable=False)
    description: str | None = Field(default=None, max_length=2000, nullable=True)
    pine_source: str = Field(nullable=False)
    pine_version: PineVersion = Field(nullable=False)
    parse_status: ParseStatus = Field(index=True, nullable=False)
    parse_errors: list[dict[str, object]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    timeframe: str | None = Field(default=None, max_length=16, nullable=True)
    symbol: str | None = Field(default=None, max_length=32, nullable=True)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    is_archived: bool = Field(default=False, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("NOW()")},
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("NOW()"),
            "onupdate": text("NOW()"),
        },
    )

"""strategy 도메인 SQLModel 테이블. Sprint 3에서 Strategy 추가."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, SQLModel

from src.common.datetime_types import AwareDateTime


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
    # Sprint 7d: market session gate. Empty list = 24h (no filter). Values are a
    # subset of {"asia", "london", "ny"} enforced at the Pydantic schema layer.
    # Nullable in DB for backward compatibility with pre-migration rows.
    trading_sessions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True, server_default="[]"),
    )
    is_archived: bool = Field(default=False, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )

"""auth 도메인 SQLModel 테이블. Sprint 3에서 User 추가."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, text
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clerk_user_id: str = Field(
        index=True,
        unique=True,
        max_length=64,
        nullable=False,
    )
    email: str | None = Field(default=None, max_length=320, nullable=True)
    username: str | None = Field(default=None, max_length=64, nullable=True)
    is_active: bool = Field(default=True, index=True, nullable=False)
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

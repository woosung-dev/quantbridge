"""auth 도메인 SQLModel 테이블. Sprint 3에서 User 추가, ADR-034 에서 Better Auth 5테이블 선언 추가."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, text
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # 외부 인증 공급자의 subject(JWT `sub`). ★내부 PK 와 분리돼 있어서 공급자를 갈아끼워도
    # FK 7곳이 그대로다 — 2026-08-17 Clerk → Better Auth 전환이 이 컬럼 하나로 끝난 이유다.
    auth_subject: str = Field(
        index=True,
        unique=True,
        max_length=64,
        nullable=False,
    )
    email: str | None = Field(default=None, max_length=320, nullable=True)
    username: str | None = Field(default=None, max_length=64, nullable=True)
    country_code: str | None = Field(default=None, max_length=2, nullable=True)
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

"""waitlist 도메인 SQLModel 테이블. Sprint 11 Phase C.

Beta 가입 대기자 신청서 — TV 구독 / 자본금 / Pine 경험 / 기존 도구 / pain_point
+ admin approve 시 HMAC invite token 발급 + Resend 로 email 발송.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, text
from sqlmodel import Column, Field, Index, SQLModel

from src.common.datetime_types import AwareDateTime


class WaitlistStatus(StrEnum):
    """신청서 상태."""

    pending = "pending"
    invited = "invited"
    joined = "joined"
    rejected = "rejected"


class WaitlistApplication(SQLModel, table=True):
    """Beta 대기자 신청서.

    email 은 unique — 중복 신청 방지. user_id 는 joined 전환 시 FK 연결.
    pain_point 는 자유 서술 (최대 1000자) — 실제 문제 의식을 걸러내는 핵심 필터.
    """

    __tablename__ = "waitlist_applications"
    __table_args__ = (
        Index("ix_waitlist_applications_status", "status"),
        Index("ix_waitlist_applications_created_at", "created_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(max_length=320, nullable=False, unique=True, index=True)
    # 본 테이블 설계의 핵심 5 질문 — Q 구체 값은 schemas.py 에서 Pydantic 으로 enforce.
    tv_subscription: str = Field(max_length=20, nullable=False)
    exchange_capital: str = Field(max_length=20, nullable=False)
    pine_experience: str = Field(max_length=20, nullable=False)
    existing_tool: str | None = Field(default=None, max_length=120, nullable=True)
    pain_point: str = Field(max_length=1000, nullable=False)

    status: WaitlistStatus = Field(
        default=WaitlistStatus.pending,
        sa_column=Column(
            # Alembic 이 `waitlist_status` 이름으로 CREATE TYPE 하므로 동일 이름 명시.
            # 기본(name 미지정) 은 lowercase class name → 'waitliststatus' 와 mismatch.
            SAEnum(WaitlistStatus, name="waitlist_status"),
            nullable=False,
        ),
    )
    invite_token: str | None = Field(default=None, max_length=512, nullable=True)
    invite_sent_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    invited_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    joined_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    user_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "user_id",
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )

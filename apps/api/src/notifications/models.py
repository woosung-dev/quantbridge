"""notifications 도메인 SQLModel 테이블 — 브라우저 푸시 구독 (pwa.md §3.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text, text
from sqlmodel import Column, Field, SQLModel

from src.common.datetime_types import AwareDateTime


class PushSubscription(SQLModel, table=True):
    """기기(브라우저) 하나의 푸시 구독.

    ★`endpoint` 가 UNIQUE 다 — 같은 브라우저가 다른 사용자로 다시 구독하면 행을 새로 만들지
    않고 **현재 사용자로 재할당**한다(공용 기기에서 이전 사용자의 알림을 받지 않게).
    """

    __tablename__ = "push_subscriptions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # 푸시 서비스 URL — 그 자체가 수신 자격이라 로그에 남기지 않는다.
    endpoint: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    p256dh: str = Field(sa_column=Column(Text, nullable=False))
    auth: str = Field(sa_column=Column(Text, nullable=False))
    user_agent: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )
    last_success_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )

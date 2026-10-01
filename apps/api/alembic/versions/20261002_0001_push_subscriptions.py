"""push_subscriptions — PWA 웹 푸시 구독 원장

Revision ID: 20261002_0001
Revises: 20260817_0002
Create Date: 2026-10-02 00:01:00.000000

docs/architecture/pwa.md §3.1. 새 테이블 하나 — 기존 행·컬럼을 건드리지 않는다.
`endpoint` UNIQUE 는 공용 기기 재할당(다른 사용자의 같은 endpoint → 현재 사용자로 이동)의
근거이고, `users` 삭제 시 CASCADE 로 함께 사라진다.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261002_0001"
down_revision: str | Sequence[str] | None = "20260817_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_success_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")

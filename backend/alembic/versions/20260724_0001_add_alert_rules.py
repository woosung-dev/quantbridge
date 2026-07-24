# 세션별 손실한도와 워치독 알림 규칙 테이블을 추가하는 마이그레이션
"""add alert rules

Revision ID: 20260724_0001
Revises: 20260723_0001
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from src.common.datetime_types import AwareDateTime

revision = "20260724_0001"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("threshold_percent", sa.Numeric(18, 8), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            AwareDateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            AwareDateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(rule_type = 'loss_limit' AND threshold_percent IS NOT NULL) "
            "OR (rule_type = 'watchdog' AND threshold_percent IS NULL)",
            name="ck_alert_rules_type_threshold",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["trading.live_signal_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="trading",
    )
    op.create_index(
        "ix_alert_rules_session_active",
        "alert_rules",
        ["session_id", "is_active"],
        schema="trading",
    )
    op.create_index(
        "uq_alert_rules_active_type",
        "alert_rules",
        ["session_id", "rule_type"],
        unique=True,
        schema="trading",
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_table("alert_rules", schema="trading")

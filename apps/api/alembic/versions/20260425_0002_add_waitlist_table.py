"""add_waitlist_applications_table

Revision ID: 20260425_0002
Revises: 20260425_0001
Create Date: 2026-04-25 00:00:02.000000

Sprint 11 Phase C — Beta Waitlist 도메인. waitlist_applications 테이블 +
waitlist_status enum 추가. FK: user_id → users(SET NULL, nullable).

Idempotency: per-object `IF NOT EXISTS` 가드 (stress_tests 마이그레이션 패턴).
conftest SQLModel.metadata.create_all 과 병행해도 schema drift 없이 적용 가능.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260425_0002"
down_revision = "20260425_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Enum ----------------
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE waitlist_status AS ENUM "
        "('pending','invited','joined','rejected'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # ---------------- Table ----------------
    bind = op.get_bind()
    table_exists = bind.execute(
        sa.text("SELECT to_regclass('public.waitlist_applications') IS NOT NULL")
    ).scalar()
    if not table_exists:
        op.create_table(
            "waitlist_applications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("tv_subscription", sa.String(length=20), nullable=False),
            sa.Column("exchange_capital", sa.String(length=20), nullable=False),
            sa.Column("pine_experience", sa.String(length=20), nullable=False),
            sa.Column("existing_tool", sa.String(length=120), nullable=True),
            sa.Column("pain_point", sa.String(length=1000), nullable=False),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "pending",
                    "invited",
                    "joined",
                    "rejected",
                    name="waitlist_status",
                    create_type=False,
                ),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("invite_token", sa.String(length=512), nullable=True),
            sa.Column("invite_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
        )

    # ---------------- Indexes ----------------
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_waitlist_applications_email "
        "ON waitlist_applications (email)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_waitlist_applications_status "
        "ON waitlist_applications (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_waitlist_applications_created_at "
        "ON waitlist_applications (created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_waitlist_applications_created_at")
    op.execute("DROP INDEX IF EXISTS ix_waitlist_applications_status")
    op.execute("DROP INDEX IF EXISTS ix_waitlist_applications_email")
    op.execute("DROP TABLE IF EXISTS waitlist_applications")
    op.execute("DROP TYPE IF EXISTS waitlist_status")

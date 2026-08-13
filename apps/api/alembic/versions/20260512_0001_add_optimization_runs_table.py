"""add_optimization_runs_table

Revision ID: 20260512_0001
Revises: 20260511_0001
Create Date: 2026-05-12 00:00:00.000000

Sprint 53 BL-228 prereq — optimization_runs 테이블 + enum (optimization_kind,
optimization_status). FK: user_id → users(CASCADE), backtest_id → backtests(RESTRICT).
RESTRICT 는 원본 backtest 삭제 시 optimization 결과 영속 유지를 위함 (StressTest 패턴 mirror).

LESSON-066 의무: SAEnum + StrEnum 조합 = DB enum value 는 member NAME (uppercase) 사용.
                 stress_test_kind 의 BL-221 P0 hotfix `da7e52e` 패턴 적용 — 처음부터
                 uppercase 'GRID_SEARCH' / 'QUEUED' 등으로 lock.

Idempotency: per-object IF NOT EXISTS 가드 (stress_tests 패턴 mirror).
Round-trip downgrade: DROP IF EXISTS 정렬 — index → table → enum.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260512_0001"
down_revision = "20260511_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Enum types ----------------
    # LESSON-066 의무 — uppercase member name (SAEnum 기본 = StrEnum.name 저장).
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE optimization_kind AS ENUM ('GRID_SEARCH'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE optimization_status AS ENUM "
        "('QUEUED','RUNNING','COMPLETED','FAILED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # ---------------- Table ----------------
    bind = op.get_bind()
    table_exists = bind.execute(
        sa.text("SELECT to_regclass('public.optimization_runs') IS NOT NULL")
    ).scalar()
    if not table_exists:
        op.create_table(
            "optimization_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "backtest_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("backtests.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "kind",
                postgresql.ENUM(
                    "GRID_SEARCH",
                    name="optimization_kind",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "QUEUED",
                    "RUNNING",
                    "COMPLETED",
                    "FAILED",
                    name="optimization_status",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "param_space",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            ),
            sa.Column(
                "result",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("celery_task_id", sa.String(64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    # ---------------- Indexes ----------------
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_optimization_runs_user_id ON optimization_runs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_optimization_runs_backtest_id "
        "ON optimization_runs (backtest_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_optimization_runs_user_created "
        "ON optimization_runs (user_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_optimization_runs_status ON optimization_runs (status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_optimization_runs_status")
    op.execute("DROP INDEX IF EXISTS ix_optimization_runs_user_created")
    op.execute("DROP INDEX IF EXISTS ix_optimization_runs_backtest_id")
    op.execute("DROP INDEX IF EXISTS ix_optimization_runs_user_id")
    op.execute("DROP TABLE IF EXISTS optimization_runs")
    op.execute("DROP TYPE IF EXISTS optimization_status")
    op.execute("DROP TYPE IF EXISTS optimization_kind")

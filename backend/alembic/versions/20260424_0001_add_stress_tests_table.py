"""add_stress_tests_table

Revision ID: 20260424_0001
Revises: 00cfa7d536e4
Create Date: 2026-04-24 00:00:00.000000

Sprint H2 Phase B — stress_tests 테이블 + enum (stress_test_kind,
stress_test_status). FK: user_id → users(CASCADE), backtest_id → backtests(RESTRICT).
RESTRICT 는 원본 backtest 삭제 시 stress test 영속 유지를 위함.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260424_0001"
down_revision = "00cfa7d536e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 멱등 보장 — 테스트 conftest 의 SQLModel.metadata.create_all 이 alembic 과
    # 병행해 같은 enum/table 을 pre-create 하는 환경에서도 성공하도록 설계.
    # enum: DO block + EXCEPTION(duplicate_object). table: check pg_class before create.
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE stress_test_kind AS ENUM ('monte_carlo','walk_forward'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE stress_test_status AS ENUM "
        "('queued','running','completed','failed'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # 존재 시 skip — conftest pre-create 대응. downgrade→upgrade roundtrip 에서는
    # 깨끗한 DB 이므로 정상 실행.
    bind = op.get_bind()
    existing = bind.execute(sa.text("SELECT to_regclass('public.stress_tests')")).scalar()
    if existing is not None:
        return

    op.create_table(
        "stress_tests",
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
                "monte_carlo",
                "walk_forward",
                name="stress_test_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "completed",
                "failed",
                name="stress_test_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
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
    op.create_index(
        "ix_stress_tests_user_id",
        "stress_tests",
        ["user_id"],
    )
    op.create_index(
        "ix_stress_tests_backtest_id",
        "stress_tests",
        ["backtest_id"],
    )
    op.create_index(
        "ix_stress_tests_user_created",
        "stress_tests",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_stress_tests_status",
        "stress_tests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_stress_tests_status", table_name="stress_tests")
    op.drop_index("ix_stress_tests_user_created", table_name="stress_tests")
    op.drop_index("ix_stress_tests_backtest_id", table_name="stress_tests")
    op.drop_index("ix_stress_tests_user_id", table_name="stress_tests")
    op.drop_table("stress_tests")
    sa.Enum(name="stress_test_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="stress_test_kind").drop(op.get_bind(), checkfirst=True)

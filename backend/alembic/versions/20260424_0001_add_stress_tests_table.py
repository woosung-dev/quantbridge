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
    # Enum 타입은 create_table 내부의 Column(Enum(...)) 이 자동으로 CREATE TYPE 하도록
    # 위임. 별도 .create() 호출 시 중복 실행 위험 (SQLAlchemy Column Enum 이 동일
    # name 에 대해 다시 CREATE TYPE 을 emit 하여 DuplicateObjectError 발생).
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
            sa.Enum(
                "monte_carlo",
                "walk_forward",
                name="stress_test_kind",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "completed",
                "failed",
                name="stress_test_status",
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

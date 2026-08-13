"""add_stress_tests_table

Revision ID: 20260424_0001
Revises: 00cfa7d536e4
Create Date: 2026-04-24 00:00:00.000000

Sprint H2 Phase B — stress_tests 테이블 + enum (stress_test_kind,
stress_test_status). FK: user_id → users(CASCADE), backtest_id → backtests(RESTRICT).
RESTRICT 는 원본 backtest 삭제 시 stress test 영속 유지를 위함.

Idempotency 정책 (iter-1 FIX-1):
    - 테스트 환경 conftest 의 `SQLModel.metadata.create_all` 이 이 마이그레이션과
      병행해 동일 enum/table 을 pre-create 한다. 이를 지원하기 위해
      **per-object `IF NOT EXISTS` 가드**를 사용한다.
    - 이전 구현은 `to_regclass('public.stress_tests')` 단일 체크로 전체 업그레이드를
      조기 return 시켰다 → 인덱스 4개가 pre-create 테이블 환경에서 전혀 생성되지
      않는 schema drift 위험이 있었음. 본 리비전에서는 각 object (enum/table/index)
      단위로 독립 idempotent guard 를 적용한다.
    - Schema drift 감지는 이 마이그레이션의 책임이 아니다 —
      `alembic check` + metadata drift 테스트 스위트 소관.
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
    # ---------------- Enum types ----------------
    # CREATE TYPE 에는 IF NOT EXISTS 가 없으므로 DO block + duplicate_object catch.
    # 이 블록은 enum 구문만 감싼다 (전체 upgrade 를 감싸지 않는다).
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

    # ---------------- Table ----------------
    # op.create_table 자체에는 if_not_exists 가 없으므로 pg_class lookup 으로 guard.
    # 테이블이 이미 존재한다면 인덱스 생성만 수행 (drift 는 별도 검증 책임).
    bind = op.get_bind()
    table_exists = bind.execute(
        sa.text("SELECT to_regclass('public.stress_tests') IS NOT NULL")
    ).scalar()
    if not table_exists:
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

    # ---------------- Indexes ----------------
    # 인덱스는 항상 실행 (테이블이 pre-create 되었더라도 누락된 인덱스를 보완).
    # PostgreSQL `CREATE INDEX IF NOT EXISTS` 사용 — schema drift 없이 idempotent.
    op.execute("CREATE INDEX IF NOT EXISTS ix_stress_tests_user_id ON stress_tests (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stress_tests_backtest_id ON stress_tests (backtest_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stress_tests_user_created "
        "ON stress_tests (user_id, created_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_stress_tests_status ON stress_tests (status)")


def downgrade() -> None:
    # DROP ... IF EXISTS — downgrade 도 idempotent. 부분 적용 상태에서 roll-back 가능.
    op.execute("DROP INDEX IF EXISTS ix_stress_tests_status")
    op.execute("DROP INDEX IF EXISTS ix_stress_tests_user_created")
    op.execute("DROP INDEX IF EXISTS ix_stress_tests_backtest_id")
    op.execute("DROP INDEX IF EXISTS ix_stress_tests_user_id")
    op.execute("DROP TABLE IF EXISTS stress_tests")
    op.execute("DROP TYPE IF EXISTS stress_test_status")
    op.execute("DROP TYPE IF EXISTS stress_test_kind")

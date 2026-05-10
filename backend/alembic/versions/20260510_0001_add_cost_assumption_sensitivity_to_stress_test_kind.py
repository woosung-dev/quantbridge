"""add cost_assumption_sensitivity to stress_test_kind enum

Sprint 50 Phase 2 — Cost Assumption Sensitivity MVP (BacktestConfig fees x slippage).

PostgreSQL 12+ 는 transaction 안 ALTER TYPE ADD VALUE 가능 (Alembic env 의
context.begin_transaction() 안 안전). PG 11 이하 시 별도 migration 필요 —
실측 환경 보장: Sprint 4 도입 timescale/timescaledb:2.14.2-pg15 (PG 15).

`IF NOT EXISTS` 가드 = idempotent 재실행 안전.

downgrade: PostgreSQL 은 enum value 제거 직접 미지원 (CREATE TYPE swap 우회 필요).
강제 downgrade 가 필요하면 별도 migration 으로 enum 재생성 swap 작성. 본 migration
은 NotImplementedError raise (codex P1#4 권고).

Revision: 20260510_0001
Down Revision: 20260507_0001
"""

from __future__ import annotations

from alembic import op

revision = "20260510_0001"
down_revision = "20260507_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG 12+ ALTER TYPE ... ADD VALUE IF NOT EXISTS — idempotent.
    op.execute("ALTER TYPE stress_test_kind ADD VALUE IF NOT EXISTS 'cost_assumption_sensitivity'")


def downgrade() -> None:
    # PostgreSQL 은 enum value 제거 직접 미지원.
    # 강제 downgrade 시 별도 migration 으로 enum 재생성 swap 작성:
    #   1. CREATE TYPE stress_test_kind_new AS ENUM ('monte_carlo', 'walk_forward')
    #   2. ALTER TABLE stress_tests ALTER COLUMN kind TYPE stress_test_kind_new
    #      USING kind::text::stress_test_kind_new
    #   3. DROP TYPE stress_test_kind
    #   4. ALTER TYPE stress_test_kind_new RENAME TO stress_test_kind
    raise NotImplementedError(
        "PostgreSQL does not support enum value removal directly. "
        "Use create-new-type swap pattern in a separate migration if downgrade is required."
    )

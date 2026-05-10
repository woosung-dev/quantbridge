"""add cost_assumption_sensitivity to stress_test_kind enum

Sprint 50 Phase 2 — Cost Assumption Sensitivity MVP (BacktestConfig fees x slippage).

PostgreSQL 12+ 는 transaction 안 ALTER TYPE ADD VALUE 가능 (Alembic env 의
context.begin_transaction() 안 안전). PG 11 이하 시 별도 migration 필요 —
실측 환경 보장: Sprint 4 도입 timescale/timescaledb:2.14.2-pg15 (PG 15).

`IF NOT EXISTS` 가드 = idempotent 재실행 안전.

downgrade: PostgreSQL ALTER TYPE ... DROP VALUE 미지원 → enum 재생성 swap pattern
(codex P1#4 권고). round-trip test (`tests/test_migrations.py::test_alembic_roundtrip`)
PASS 의무.

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
    # Init migration `20260424_0001` 이 SAEnum default mapping 으로 enum value 를
    # member name (uppercase 'MONTE_CARLO' / 'WALK_FORWARD') 으로 생성 → 일관성을
    # 위해 신규 value 도 uppercase 사용 의무. Playwright e2e 시 발견:
    # lowercase 추가 시 SQLAlchemy INSERT 가 member name 보내
    # InvalidTextRepresentationError → 500 error (BL-221 회고).
    op.execute("ALTER TYPE stress_test_kind ADD VALUE IF NOT EXISTS 'COST_ASSUMPTION_SENSITIVITY'")


def downgrade() -> None:
    """Enum value rollback — PostgreSQL swap pattern (codex P1#4).

    PostgreSQL 은 ALTER TYPE ... DROP VALUE 미지원 → enum 재생성 swap.

    Pre-condition: stress_tests 테이블 안 kind='COST_ASSUMPTION_SENSITIVITY' row 가
    없어야 함. 잔존 시 마지막 USING cast 가 fail → 운영 downgrade 시 사용자가
    먼저 해당 row 정리 의무 (DELETE FROM stress_tests WHERE kind =
    'COST_ASSUMPTION_SENSITIVITY'). round-trip test 환경 (빈 DB) 에서는 안전.

    Init migration `20260424_0001` 의 enum value 는 SAEnum member name
    (uppercase) — 'MONTE_CARLO' / 'WALK_FORWARD' 그대로 재생성.

    Swap chain:
      1. column 을 TEXT 로 임시 detach (enum 의존성 끊기)
      2. 기존 enum DROP
      3. COST_ASSUMPTION_SENSITIVITY 제외한 enum 재생성
      4. column 을 새 enum 으로 cast 복원
    """
    op.execute("ALTER TABLE stress_tests ALTER COLUMN kind TYPE TEXT")
    op.execute("DROP TYPE stress_test_kind")
    op.execute("CREATE TYPE stress_test_kind AS ENUM ('MONTE_CARLO', 'WALK_FORWARD')")
    op.execute(
        "ALTER TABLE stress_tests ALTER COLUMN kind TYPE stress_test_kind "
        "USING kind::text::stress_test_kind"
    )

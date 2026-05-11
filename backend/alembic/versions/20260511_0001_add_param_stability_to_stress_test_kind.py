"""add param_stability to stress_test_kind enum

Sprint 51 Phase 2 — Param Stability (pine_v2 input override grid sweep).

PostgreSQL 12+ 는 transaction 안 ALTER TYPE ADD VALUE 가능 (Alembic env 의
context.begin_transaction() 안 안전). 실측 환경: timescale/timescaledb:2.14.2-pg15.

`IF NOT EXISTS` 가드 = idempotent 재실행 안전.

LESSON-066 (Sprint 50 BL-221 P0 hotfix `da7e52e`) 의무 = 신규 enum value 는
init migration 의 SAEnum member name (uppercase) 와 일관성 유지. Sprint 51 =
LESSON-066 2차 검증 path (Slice 6 Playwright e2e 풀 chain).

downgrade: PostgreSQL ALTER TYPE ... DROP VALUE 미지원 → enum 재생성 swap pattern
(Sprint 50 commit `5945070` reuse). round-trip test PASS 의무.

Revision: 20260511_0001
Down Revision: 20260510_0001
"""

from __future__ import annotations

from alembic import op

revision = "20260511_0001"
down_revision = "20260510_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG 12+ ALTER TYPE ... ADD VALUE IF NOT EXISTS — idempotent.
    # uppercase 의무 (LESSON-066): SAEnum + StrEnum member name 일관성. lowercase 추가 시
    # SQLAlchemy INSERT 가 member name 으로 보내 InvalidTextRepresentationError → 500 error
    # (Sprint 50 BL-221 1차 발견). Sprint 51 = 2차 검증 path (Slice 6 Playwright e2e).
    op.execute("ALTER TYPE stress_test_kind ADD VALUE IF NOT EXISTS 'PARAM_STABILITY'")


def downgrade() -> None:
    """Enum value rollback — PostgreSQL swap pattern (Sprint 50 commit 5945070 reuse).

    PostgreSQL 은 ALTER TYPE ... DROP VALUE 미지원 → enum 재생성 swap.

    Pre-condition: stress_tests 테이블 안 kind='PARAM_STABILITY' row 가
    없어야 함. 잔존 시 마지막 USING cast 가 fail → 운영 downgrade 시 사용자가
    먼저 해당 row 정리 의무 (DELETE FROM stress_tests WHERE kind =
    'PARAM_STABILITY'). round-trip test 환경 (빈 DB) 에서는 안전.

    재생성 시 Sprint 50 의 COST_ASSUMPTION_SENSITIVITY 도 보존 — Sprint 50 migration
    이 이미 적용된 상태에서 Sprint 51 만 rollback 하는 시나리오.

    Swap chain:
      1. column 을 TEXT 로 임시 detach (enum 의존성 끊기)
      2. 기존 enum DROP
      3. PARAM_STABILITY 제외한 enum 재생성 (MONTE_CARLO / WALK_FORWARD / COST_ASSUMPTION_SENSITIVITY)
      4. column 을 새 enum 으로 cast 복원
    """
    op.execute("ALTER TABLE stress_tests ALTER COLUMN kind TYPE TEXT")
    op.execute("DROP TYPE stress_test_kind")
    op.execute(
        "CREATE TYPE stress_test_kind AS ENUM "
        "('MONTE_CARLO', 'WALK_FORWARD', 'COST_ASSUMPTION_SENSITIVITY')"
    )
    op.execute(
        "ALTER TABLE stress_tests ALTER COLUMN kind TYPE stress_test_kind "
        "USING kind::text::stress_test_kind"
    )

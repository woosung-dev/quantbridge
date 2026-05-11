"""add genetic to optimization_kind enum

Sprint 56 BL-233 — Genetic executor 본격 진입 prereq. Sprint 55 BAYESIAN 마이그레이션
(`20260513_0001`) 1:1 mirror, value 만 `GENETIC` 으로 교체.

PostgreSQL 12+ 는 transaction 안 ALTER TYPE ADD VALUE 가능.
`IF NOT EXISTS` 가드 = idempotent 재실행 안전.

LESSON-066 7차 영구 검증 path = SAEnum + StrEnum member name (uppercase) 일관성.
lowercase 'genetic' 추가 시 SQLAlchemy INSERT 가 member name (uppercase 'GENETIC')
으로 보내 InvalidTextRepresentationError 500 위험 (Sprint 50 BL-221 1차 패턴 재발).

downgrade: PostgreSQL ALTER TYPE ... DROP VALUE 미지원 → enum 재생성 swap pattern
(Sprint 50 commit `5945070` + Sprint 51 BL-145 + Sprint 55 mirror). round-trip
test PASS 의무.

Revision: 20260514_0001
Down Revision: 20260513_0001
"""

from __future__ import annotations

from alembic import op

revision = "20260514_0001"
down_revision = "20260513_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG 12+ ALTER TYPE ... ADD VALUE IF NOT EXISTS — idempotent.
    # uppercase 의무 (LESSON-066): SAEnum + StrEnum member name 일관성.
    op.execute("ALTER TYPE optimization_kind ADD VALUE IF NOT EXISTS 'GENETIC'")


def downgrade() -> None:
    """Enum value rollback — PostgreSQL swap pattern (Sprint 55 mirror).

    PostgreSQL 은 ALTER TYPE ... DROP VALUE 미지원 → enum 재생성 swap.

    Pre-condition: optimization_runs 테이블 안 kind='GENETIC' row 가
    없어야 함. 잔존 시 마지막 USING cast 가 fail → 운영 downgrade 시 사용자가
    먼저 해당 row 정리 의무 (DELETE FROM optimization_runs WHERE kind = 'GENETIC').
    round-trip test 환경 (빈 DB) 에서는 안전.

    Swap chain:
      1. column 을 TEXT 로 임시 detach (enum 의존성 끊기)
      2. 기존 enum DROP
      3. GENETIC 제외한 enum 재생성 (GRID_SEARCH + BAYESIAN)
      4. column 을 새 enum 으로 cast 복원
    """
    op.execute("ALTER TABLE optimization_runs ALTER COLUMN kind TYPE TEXT")
    op.execute("DROP TYPE optimization_kind")
    op.execute("CREATE TYPE optimization_kind AS ENUM ('GRID_SEARCH', 'BAYESIAN')")
    op.execute(
        "ALTER TABLE optimization_runs ALTER COLUMN kind TYPE optimization_kind "
        "USING kind::text::optimization_kind"
    )

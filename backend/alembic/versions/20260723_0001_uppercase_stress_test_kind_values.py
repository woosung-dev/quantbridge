# stress_test 계열 enum 의 소문자 레거시 라벨을 SAEnum 저장 규약(member NAME, 대문자)으로 정렬하는 migration
"""uppercase stress_test enum legacy values (kind + status)

functional-parity 2026-07-23 실브라우저 dogfood 실측 — POST /stress-tests/monte-carlo 가
실 DB 에서 500: `invalid input value for enum stress_test_kind: "MONTE_CARLO"`.

원인: 최초 migration(20260424_0001)이 stress_test_kind('monte_carlo','walk_forward')와
stress_test_status('queued','running','completed','failed')를 소문자로 생성했고, 이후
LESSON-066(Sprint 50 BL-221 hotfix `da7e52e`)이 신규 kind 값들을 대문자
(COST_ASSUMPTION_SENSITIVITY/PARAM_STABILITY)로 추가하면서 **레거시 라벨은 미정렬**로
남았다. SAEnum(StrEnum) 은 member NAME(대문자)을 저장하므로 alembic 제공 DB 에서
Monte Carlo / Walk-Forward 생성이 전부 실패한다. (원본 CREATE 는
`duplicate_object THEN NULL` 가드라 metadata 로 먼저 생성된 DB 에선 조용히 기존
타입을 유지 — DB 이력에 따라 라벨 케이싱이 갈라지는 구조였다.)

테스트 DB 는 metadata 생성(대문자 일관)이라 이 드리프트를 못 잡았다 — sentinel 은
tests/test_migrations.py::test_stress_test_enum_labels_match_member_names.

RENAME VALUE 는 기존 저장 row 의 값도 함께 바꾸므로 데이터 이행이 따로 필요 없다.
(PG 10+, 트랜잭션 내 실행 가능 — ADD VALUE 와 달리 제약 없음.) 라벨 부재 시 skip
하는 idempotent 가드라 metadata 생성 DB(이미 대문자)에도 안전하다.

Revision ID: 20260723_0001
Revises: 20260705_0001
Create Date: 2026-07-23
"""

from alembic import op

revision = "20260723_0001"
down_revision = "20260705_0001"
branch_labels = None
depends_on = None

_RENAMES: list[tuple[str, str, str]] = [
    ("stress_test_kind", "monte_carlo", "MONTE_CARLO"),
    ("stress_test_kind", "walk_forward", "WALK_FORWARD"),
    ("stress_test_status", "queued", "QUEUED"),
    ("stress_test_status", "running", "RUNNING"),
    ("stress_test_status", "completed", "COMPLETED"),
    ("stress_test_status", "failed", "FAILED"),
]


def _rename_if_present(type_name: str, old: str, new: str) -> None:
    # S608: 인자 3종 전부 본 모듈의 하드코딩 상수(_RENAMES) — 외부 입력 경로 없음.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{type_name}' AND e.enumlabel = '{old}'
            ) THEN
                ALTER TYPE {type_name} RENAME VALUE '{old}' TO '{new}';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    for type_name, old, new in _RENAMES:
        _rename_if_present(type_name, old, new)


def downgrade() -> None:
    for type_name, old, new in _RENAMES:
        _rename_if_present(type_name, new, old)

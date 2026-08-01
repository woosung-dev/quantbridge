# deactivated_reason 이 정본 enum 밖 값을 못 받게 원장에 CHECK 를 건다 (BL-571)
"""check live session deactivated reason

Revision ID: 20260801_0001
Revises: 20260730_0001
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0001"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_live_signal_sessions_deactivated_reason"
_TABLE = "trading.live_signal_sessions"

# ★값 집합의 정본은 src/trading/models.py 의 SessionDeactivationReason 이다.
# 마이그레이션은 스냅샷이라 그 시점 값을 동결해서 적는다(런타임 import 금지 — 나중에 enum 이
# 바뀌면 과거 마이그레이션의 의미까지 바뀐다). 동결본이 정본과 어긋나면
# tests/test_migrations.py::test_deactivation_reason_check_matches_the_enum 이 잡는다.
_REASONS = (
    "coverage_unrunnable",
    "degraded_unconsented",
    "equity_baseline_missing",
    "equity_exhausted",
    "run_live_error",
    "runtime_divergence",
    "gap_resync_position_mismatch",
    "position_divergence",
    "user_stopped",
)

_CHECK = "deactivated_reason IS NULL OR deactivated_reason IN ({})".format(
    ", ".join(f"'{reason}'" for reason in _REASONS)
)


def upgrade() -> None:
    # ★NOT VALID 인 이유 — 이 마이그레이션 시점의 원장에는 운영자가 soak 중 psql 로 직접 써넣은
    # enum 밖 값(soak_closed_by_operator / interim_window_stop / prefix_w1_window_done)이 남아
    # 있다. 그 행 정리는 BL-571 (a) 로 분리돼 있어 여기서 건드리지 않는다. 검증 스캔이 붙은
    # 평범한 ADD CONSTRAINT 는 그 행들 때문에 실패해 제약이 아예 안 붙는다.
    # NOT VALID 는 **기존 행 스캔만** 건너뛴다 — 이후 모든 INSERT/UPDATE 는 그대로 검사한다
    # (= 재발 차단은 지금부터 작동). (a) 정리가 끝나면 별도 마이그레이션에서
    # `VALIDATE CONSTRAINT` 로 과거까지 닫으면 된다.
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} CHECK ({_CHECK}) NOT VALID")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")

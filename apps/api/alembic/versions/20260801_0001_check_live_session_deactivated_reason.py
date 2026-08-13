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


# BL-571 (a) — 운영자가 soak 중 psql 로 직접 써넣은 값. 코드가 만든 적이 없다
# (`apps/api/` · `scripts/` grep 0건). 셋 다 "사람이 창을 닫았다" 이므로 정본 `user_stopped` 로 접는다.
_OPERATOR_WRITTEN = ("soak_closed_by_operator", "interim_window_stop", "prefix_w1_window_done")


def upgrade() -> None:
    # ★(a) 정리를 여기 넣는 이유 — 원래 이 정리는 CONTROL 이 psql 로 한 번 치는 수동 작업이었다.
    # 그러면 재현이 셸 히스토리에만 남고, 다른 환경은 영원히 오염된 채로 남는다.
    # 오염을 만든 것이 "원장 직접 쓰기" 였는데 그 해소도 원장 직접 쓰기로 두면 같은 병이다.
    op.execute(
        f"UPDATE {_TABLE} SET deactivated_reason = 'user_stopped' "
        f"WHERE deactivated_reason IN ({', '.join(repr(r) for r in _OPERATOR_WRITTEN)})"
    )

    # ★NOT VALID 로 먼저 붙인다 — 아래 VALIDATE 를 별도 단계로 두어야 실패 지점이 분명해진다.
    # NOT VALID 는 **기존 행 스캔만** 건너뛴다. 이후 INSERT/UPDATE 는 그대로 검사하므로
    # 재발 차단은 이 줄부터 작동한다.
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} CHECK ({_CHECK}) NOT VALID")

    # ★남은 위반을 **찍으면서** 멈춘다. VALIDATE 를 그냥 돌리면 Postgres 는 제약 이름만 말하고
    # 어떤 값이 걸렸는지는 안 알려준다 — 이 스프린트가 고치고 있는 바로 그 침묵이다.
    # 우리가 아는 3종 말고 다른 값이 있다면 그건 사람이 판단할 일이지 마이그레이션이
    # 조용히 삼킬 일이 아니다.
    leftovers = [
        row[0]
        for row in op.get_bind().exec_driver_sql(
            f"SELECT DISTINCT deactivated_reason FROM {_TABLE} "
            f"WHERE deactivated_reason IS NOT NULL AND NOT ({_CHECK})"
        )
    ]
    if leftovers:
        raise RuntimeError(
            "deactivated_reason 에 정본 밖 값이 남아 있어 제약을 확정할 수 없다: "
            f"{sorted(leftovers)}. 값마다 정본 사유로 접거나 "
            "src/trading/models.py 의 SessionDeactivationReason 에 정식 등재한 뒤 다시 돌려라."
        )

    # 과거까지 닫는다. 여기까지 오면 위반 행이 0 임이 위에서 확인된 상태다.
    op.execute(f"ALTER TABLE {_TABLE} VALIDATE CONSTRAINT {_CONSTRAINT}")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")

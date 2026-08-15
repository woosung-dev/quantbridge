# 세션 종료 사유에 `account_deleted` 를 추가한다 (2026-08-15 surface-truth · S3).
"""add account_deleted to deactivated_reason check

Clerk `user.deleted` 웹훅이 소유자의 라이브 세션을 전량 내리게 되면서 새 사유가 하나 생겼다.
`ck_live_signal_sessions_deactivated_reason` 은 값 집합을 **원장에서** 못박으므로([BL-571]),
enum 에만 추가하면 실제로 세션을 내리는 순간 `IntegrityError` 로 **종료가 실패**한다 —
라벨 오염보다 나쁜 고장이다.

★값 집합의 정본은 `src/trading/models.py` 의 `SessionDeactivationReason` 이다. 마이그레이션은
스냅샷이라 **그 시점 값을 동결해서** 적는다(런타임 import 금지 — 나중에 enum 이 바뀌면 과거
마이그레이션의 의미까지 바뀐다). 동결본이 정본과 어긋나면
`tests/test_migrations.py::test_deactivation_reason_check_matches_the_enum` 이 잡는다.

★`user_stopped` 로 접지 않은 이유 — 탈퇴한 사람은 Stop 을 누른 적이 없다. 이 스프린트의
주제가 「화면이 사실이 아닌 것을 말한다」이므로 여기서 거짓 라벨을 새로 만들지 않는다.

★기존 행 스캔은 필요 없다 — 값 집합이 **넓어지기만** 하므로 과거에 통과한 행은 전부 통과한다.
그래서 `20260801_0001` 의 NOT VALID → VALIDATE 2단 절차 대신 한 번에 붙인다.

Revision ID: 20260815_0003
Revises: 20260815_0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260815_0003"
down_revision: str | Sequence[str] | None = "20260815_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_live_signal_sessions_deactivated_reason"
_TABLE = "trading.live_signal_sessions"

# 2026-08-15 시점의 SessionDeactivationReason 동결본 (= 20260801_0001 의 9종 + account_deleted).
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
    "account_deleted",
)

# 되돌릴 때 복원할 집합 = 20260801_0001 의 동결본.
_PREVIOUS_REASONS = tuple(r for r in _REASONS if r != "account_deleted")


def _check(reasons: Sequence[str]) -> str:
    return "deactivated_reason IS NULL OR deactivated_reason IN ({})".format(
        ", ".join(f"'{reason}'" for reason in reasons)
    )


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} CHECK ({_check(_REASONS)})")


def downgrade() -> None:
    # ★좁히는 방향이라 위반 행이 남아 있을 수 있다 — 조용히 삼키지 말고 **찍으면서** 멈춘다
    #   (`20260801_0001` 이 세운 선례).
    leftovers = [
        row[0]
        for row in op.get_bind().exec_driver_sql(
            f"SELECT DISTINCT deactivated_reason FROM {_TABLE} "
            f"WHERE deactivated_reason IS NOT NULL AND NOT ({_check(_PREVIOUS_REASONS)})"
        )
    ]
    if leftovers:
        raise RuntimeError(
            "downgrade 하면 CHECK 를 위반하게 되는 행이 남아 있다: "
            f"{sorted(leftovers)}. 값마다 정본 사유로 접은 뒤 다시 돌려라."
        )
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} CHECK ({_check(_PREVIOUS_REASONS)})"
    )

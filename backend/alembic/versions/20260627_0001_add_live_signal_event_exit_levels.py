"""add_live_signal_event_exit_levels

Revision ID: 20260627_0001
Revises: 20260626_0002
Create Date: 2026-06-27 00:00:00.000000

Phase 3 (라이브 exit-level surfacing) — trading.live_signal_events 에 entry signal 의
exit 레벨 컬럼 추가. take_profit/stop_loss(bracket placement) + trailing_stop(Bybit
native trailing 거리). event-loop 가 pending_exits 에서 fold, dispatch task 가
OrderRequest 로 전파. 전부 nullable = 기존 entry/close event row 회귀 0.
enum swap 아님 — 안전한 ADD COLUMN. up→down→up round-trip.

Idempotent ADD/DROP COLUMN IF (NOT) EXISTS (20260626_0002 패턴 mirror).
"""

from __future__ import annotations

from alembic import op

revision = "20260627_0001"
down_revision = "20260626_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE trading.live_signal_events ADD COLUMN IF NOT EXISTS take_profit NUMERIC(18, 8)"
    )
    op.execute(
        "ALTER TABLE trading.live_signal_events ADD COLUMN IF NOT EXISTS stop_loss NUMERIC(18, 8)"
    )
    op.execute(
        "ALTER TABLE trading.live_signal_events ADD COLUMN IF NOT EXISTS trailing_stop NUMERIC(18, 8)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE trading.live_signal_events DROP COLUMN IF EXISTS trailing_stop")
    op.execute("ALTER TABLE trading.live_signal_events DROP COLUMN IF EXISTS stop_loss")
    op.execute("ALTER TABLE trading.live_signal_events DROP COLUMN IF EXISTS take_profit")

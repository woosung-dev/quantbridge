"""add_realized_pnl_to_live_signal_events

Revision ID: 20260529_0001
Revises: 20260514_0001
Create Date: 2026-05-29 00:00:00.000000

MP-1 — live_signal_events.realized_pnl 컬럼 추가. close 이벤트의 청산 realized PnL
(event-loop 계산)을 저장하여 dispatch task 가 Order.realized_pnl 로 전파한다. 이전엔
Order.realized_pnl 이 어떤 경로에서도 기록되지 않아 kill-switch CumulativeLoss/DailyLoss
평가기가 SUM(realized_pnl)=0 으로 영구 inert 였다 (audit MP-1, CRITICAL).

Nullable — entry 이벤트는 None. Idempotent ADD/DROP COLUMN IF (NOT) EXISTS (table 패턴 mirror).
"""

from __future__ import annotations

from alembic import op

revision = "20260529_0001"
down_revision = "20260514_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE trading.live_signal_events "
        "ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC(18, 8)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE trading.live_signal_events DROP COLUMN IF EXISTS realized_pnl")

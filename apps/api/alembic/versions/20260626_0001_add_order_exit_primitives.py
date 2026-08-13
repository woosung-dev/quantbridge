"""add_order_exit_primitives

Revision ID: 20260626_0001
Revises: 20260529_0001
Create Date: 2026-06-26 00:00:00.000000

Wave 1 (TP/SL order primitives) — trading.orders 에 라이브 손익보호 프리미티브 컬럼 추가.
reduce_only(close over-fill 방지) + trigger_price/trigger_by(standalone trigger) +
take_profit/stop_loss(bracket attach). 전부 nullable / reduce_only 는 NOT NULL DEFAULT false
= 기존 entry 주문 row 회귀 0. enum swap 아님 — 안전한 ADD COLUMN.

Idempotent ADD/DROP COLUMN IF (NOT) EXISTS (table 패턴 mirror).
"""

from __future__ import annotations

from alembic import op

revision = "20260626_0001"
down_revision = "20260529_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE trading.orders "
        "ADD COLUMN IF NOT EXISTS reduce_only BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS trigger_price NUMERIC(18, 8)")
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS trigger_by VARCHAR(16)")
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS take_profit NUMERIC(18, 8)")
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS stop_loss NUMERIC(18, 8)")


def downgrade() -> None:
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS stop_loss")
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS take_profit")
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS trigger_by")
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS trigger_price")
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS reduce_only")

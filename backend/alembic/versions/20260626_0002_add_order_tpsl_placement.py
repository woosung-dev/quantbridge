"""add_order_tpsl_placement

Revision ID: 20260626_0002
Revises: 20260626_0001
Create Date: 2026-06-26 00:00:01.000000

Wave 2 (TP/SL placement) — trading.orders 에 standalone 트리거/트레일링 placement 컬럼 추가.
trigger_direction(Bybit v5 1=rise/2=fall) + oco_group_id(app-side OCO 형제 추적) +
trailing_stop(Bybit native trailing). 전부 nullable = 기존 entry/exit 주문 row 회귀 0.
enum swap 아님 — 안전한 ADD COLUMN. up→down→up round-trip.

Idempotent ADD/DROP COLUMN IF (NOT) EXISTS (Wave 1 20260626_0001 패턴 mirror).
"""

from __future__ import annotations

from alembic import op

revision = "20260626_0002"
down_revision = "20260626_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS trigger_direction INTEGER")
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS oco_group_id VARCHAR(64)")
    op.execute("ALTER TABLE trading.orders ADD COLUMN IF NOT EXISTS trailing_stop NUMERIC(18, 8)")


def downgrade() -> None:
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS trailing_stop")
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS oco_group_id")
    op.execute("ALTER TABLE trading.orders DROP COLUMN IF EXISTS trigger_direction")

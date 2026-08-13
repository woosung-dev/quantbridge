# 주문의 거래소 확정 손익 동기화 시각을 추가하는 마이그레이션
"""add order realized pnl synced at

Revision ID: 20260725_0001
Revises: 20260724_0002
Create Date: 2026-07-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260725_0001"
down_revision = "20260724_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("realized_pnl_synced_at", sa.DateTime(timezone=True), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.drop_column("orders", "realized_pnl_synced_at", schema="trading")

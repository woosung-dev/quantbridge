# LiveSignalSession의 세션 시작 시점 총자본 기준선을 추가하는 마이그레이션
"""add live session equity baseline

Revision ID: 20260726_0001
Revises: 20260725_0002
Create Date: 2026-07-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260726_0001"
down_revision = "20260725_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "live_signal_sessions",
        sa.Column("equity_baseline_usdt", sa.Numeric(18, 8), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE trading.live_signal_sessions DROP COLUMN IF EXISTS equity_baseline_usdt"
    )

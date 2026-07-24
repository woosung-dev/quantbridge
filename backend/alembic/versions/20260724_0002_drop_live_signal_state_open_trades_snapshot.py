# LiveSignalState의 미사용 open trades snapshot 컬럼을 제거하는 마이그레이션
"""drop live signal state open trades snapshot

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260724_0002"
down_revision = "20260724_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("live_signal_states", "last_open_trades_snapshot", schema="trading")


def downgrade() -> None:
    op.add_column(
        "live_signal_states",
        sa.Column(
            "last_open_trades_snapshot",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="trading",
    )

"""add_equity_curve_to_live_signal_states

Revision ID: 20260504_0002
Revises: 20260504_0001
Create Date: 2026-05-04 18:00:00.000000

Sprint 28 Slice 3 (BL-140b) — `trading.live_signal_states.equity_curve` JSONB
nullable 컬럼. PR #104 의 Activity Timeline chart placeholder (events entry/close
누적) 후속 — real cumulative realized PnL 누적 array.

schema: equity_curve = [{"timestamp_ms": 1700000000000, "cumulative_pnl": "0.123"}]

nullable=True: legacy row (Sprint 26-27 active LiveSignal) 는 backfill empty
array `[]` 로 초기화 — 안전 (정확한 재계산은 manual recompute UI 후속 BL).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260504_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add equity_curve JSONB column (nullable) + backfill empty array."""
    op.add_column(
        "live_signal_states",
        sa.Column(
            "equity_curve",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema="trading",
    )

    # Backfill existing active rows: empty array
    # (정확한 재계산은 후속 manual recompute UI — BL 등록)
    op.execute(
        "UPDATE trading.live_signal_states SET equity_curve = '[]'::jsonb "
        "WHERE equity_curve IS NULL"
    )


def downgrade() -> None:
    """Remove equity_curve column."""
    op.drop_column("live_signal_states", "equity_curve", schema="trading")

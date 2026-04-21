"""add_backtest_idempotency_key

Revision ID: 20260421_0002
Revises: 7d0a0b0c0d0e
Create Date: 2026-04-21 00:02:00.000000

Sprint 9-6 — idempotency_key column on backtests table.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260421_0002"
down_revision = "7d0a0b0c0d0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("idempotency_key", sa.String(128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_backtests_idempotency_key",
        "backtests",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_backtests_idempotency_key", "backtests", type_="unique")
    op.drop_column("backtests", "idempotency_key")

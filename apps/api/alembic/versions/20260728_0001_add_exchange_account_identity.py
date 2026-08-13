"""add exchange account identity

Revision ID: 20260728_0001
Revises: 20260726_0001
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260728_0001"
down_revision = "20260726_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exchange_accounts",
        sa.Column("exchange_uid", sa.String(length=64), nullable=True),
        schema="trading",
    )
    op.add_column(
        "exchange_accounts",
        sa.Column("read_only", sa.Boolean(), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.execute("ALTER TABLE trading.exchange_accounts DROP COLUMN IF EXISTS read_only")
    op.execute("ALTER TABLE trading.exchange_accounts DROP COLUMN IF EXISTS exchange_uid")

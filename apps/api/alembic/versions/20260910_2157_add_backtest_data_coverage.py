"""add backtest data coverage

Revision ID: 20260910_0001
Revises: 20260817_0002
Create Date: 2026-09-10 21:57:42.306567

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260910_0001"
down_revision: str | Sequence[str] | None = "20260817_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("data_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtests", "data_coverage")

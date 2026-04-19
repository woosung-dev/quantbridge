"""sprint7d_okx_trading_sessions

Revision ID: 7d0a0b0c0d0e
Revises: edc2c1c4c313
Create Date: 2026-04-19 12:00:00.000000

Sprint 7d — OKX adapter + Trading Sessions filter.

Changes:
1. Extend ``exchangename`` ENUM with ``okx``. ``ADD VALUE`` must run outside a
   transaction block, so an autocommit block is used. Downgrade cannot drop enum
   values in PostgreSQL — the value stays in place; this is documented and is a
   one-way change.
2. Add ``trading.exchange_accounts.passphrase_encrypted`` (LargeBinary NULL) —
   OKX-only auth field. Existing Bybit rows keep NULL.
3. Add ``public.strategies.trading_sessions`` (JSONB NULL, default ``'[]'``) —
   list of allowed market sessions. Empty/NULL means 24h.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d0a0b0c0d0e"
down_revision: str | Sequence[str] | None = "edc2c1c4c313"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Extend exchangename enum with 'okx'. ALTER TYPE ... ADD VALUE cannot run
    #    inside a transaction, hence autocommit_block + IF NOT EXISTS for idempotency.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE exchangename ADD VALUE IF NOT EXISTS 'okx'")

    # 2. exchange_accounts.passphrase_encrypted (OKX-only, nullable).
    op.add_column(
        "exchange_accounts",
        sa.Column("passphrase_encrypted", sa.LargeBinary(), nullable=True),
        schema="trading",
    )

    # 3. strategies.trading_sessions JSONB NULL default '[]'.
    op.add_column(
        "strategies",
        sa.Column(
            "trading_sessions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("strategies", "trading_sessions")
    op.drop_column("exchange_accounts", "passphrase_encrypted", schema="trading")
    # NOTE: PostgreSQL does not support dropping enum values. The 'okx' value in
    # exchangename is left in place on downgrade — re-running upgrade is a no-op
    # thanks to IF NOT EXISTS.

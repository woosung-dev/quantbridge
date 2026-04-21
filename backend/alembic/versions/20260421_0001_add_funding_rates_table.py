"""add_funding_rates_table

Revision ID: 20260421_0001
Revises: 7d0a0b0c0d0e
Create Date: 2026-04-21 00:01:00.000000

Sprint PR-C — trading.funding_rates 테이블 신규 생성.
8시간 주기 Bybit/OKX funding rate 기록 저장.
UNIQUE: (exchange, symbol, funding_timestamp) — 중복 수집 방지.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260421_0001"
down_revision: str = "7d0a0b0c0d0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "funding_rates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("funding_rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("funding_timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exchange",
            "symbol",
            "funding_timestamp",
            name="uq_funding_rates_exchange_symbol_ts",
        ),
        schema="trading",
    )
    op.create_index(
        "ix_funding_rates_exchange_symbol",
        "funding_rates",
        ["exchange", "symbol"],
        schema="trading",
    )


def downgrade() -> None:
    op.drop_index("ix_funding_rates_exchange_symbol", table_name="funding_rates", schema="trading")
    op.drop_table("funding_rates", schema="trading")

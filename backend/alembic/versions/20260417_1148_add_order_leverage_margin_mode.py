"""add_order_leverage_margin_mode

Revision ID: edc2c1c4c313
Revises: faa9ad7b4585
Create Date: 2026-04-17 11:48:08.444697

Sprint 7a T1 — trading.orders 테이블에 Futures/Margin 지원용 컬럼 추가.

- leverage INTEGER NULL       : Bybit Linear Perp 레버리지 (Spot은 NULL)
- margin_mode VARCHAR(16) NULL: "cross" | "isolated" (Spot은 NULL)

Spot 경로는 두 컬럼 모두 NULL 유지. 기존 Sprint 6 주문은 backfill 불필요.

NOTE:
- autogenerate가 `trading.orders` 를 "새 테이블"로 잘못 감지하는 문제가 있어
  (create_trading_schema.py 주석 참조) 본 마이그레이션은 수동 작성됨.
- downgrade는 컬럼만 drop — 기존 데이터는 NULL이므로 무손실.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'edc2c1c4c313'
down_revision: str | Sequence[str] | None = 'faa9ad7b4585'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("leverage", sa.Integer(), nullable=True),
        schema="trading",
    )
    op.add_column(
        "orders",
        sa.Column("margin_mode", sa.String(length=16), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.drop_column("orders", "margin_mode", schema="trading")
    op.drop_column("orders", "leverage", schema="trading")

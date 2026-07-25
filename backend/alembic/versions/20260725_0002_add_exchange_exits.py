# 거래소 원본 청산 기록을 행 단위로 보존하는 원장 테이블을 추가하는 마이그레이션
"""거래소 청산 원장 테이블을 추가한다.

Revision ID: 20260725_0002
Revises: 20260725_0001
Create Date: 2026-07-25
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from src.common.datetime_types import AwareDateTime

revision = "20260725_0002"
down_revision = "20260725_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchange_exits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange_order_id", sa.String(length=120), nullable=False),
        sa.Column("row_hash", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("closed_pnl", sa.Numeric(18, 8), nullable=False),
        sa.Column("closed_size", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_entry_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("exchange_created_at", AwareDateTime(), nullable=False),
        sa.Column("exchange_updated_at", AwareDateTime(), nullable=True),
        sa.Column("classification", sa.String(length=24), nullable=False),
        sa.Column("create_type", sa.String(length=32), nullable=True),
        sa.Column("stop_order_type", sa.String(length=32), nullable=True),
        sa.Column("order_link_id", sa.String(length=120), nullable=True),
        sa.Column("matched_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attributed_strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attribution_confidence", sa.String(length=16), nullable=False),
        sa.Column("raw", postgresql.JSONB(none_as_null=True), nullable=False),
        sa.Column(
            "created_at",
            AwareDateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            AwareDateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["exchange_account_id"],
            ["trading.exchange_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["matched_order_id"], ["trading.orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["attributed_strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="trading",
    )
    op.create_index(
        "uq_exchange_exits_row",
        "exchange_exits",
        ["exchange_account_id", "row_hash"],
        unique=True,
        schema="trading",
    )
    op.create_index(
        "ix_exchange_exits_account_created",
        "exchange_exits",
        ["exchange_account_id", "exchange_created_at"],
        schema="trading",
    )
    op.create_index(
        "ix_exchange_exits_classification",
        "exchange_exits",
        ["classification"],
        schema="trading",
    )
    # 과거 적재 진행 상태는 원장 min 으로 파생할 수 없다. 청산이 없던 구간을 만나면
    # 삽입이 0 이라 min 이 안 움직여 같은 빈 창을 영원히 재조회한다.
    op.create_table(
        "exchange_exit_sync_state",
        sa.Column("exchange_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backfilled_from", AwareDateTime(), nullable=True),
        sa.Column(
            "created_at",
            AwareDateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            AwareDateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["exchange_account_id"],
            ["trading.exchange_accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("exchange_account_id"),
        schema="trading",
    )


def downgrade() -> None:
    # DROP 은 IF EXISTS 로 쓴다. 부분 적용된 환경에서 downgrade 가 중간에 죽으면
    # 되돌릴 방법이 없어진다(이 레포 교훈).
    op.execute("DROP TABLE IF EXISTS trading.exchange_exit_sync_state")
    op.execute("DROP INDEX IF EXISTS trading.ix_exchange_exits_classification")
    op.execute("DROP INDEX IF EXISTS trading.ix_exchange_exits_account_created")
    op.execute("DROP INDEX IF EXISTS trading.uq_exchange_exits_row")
    op.execute("DROP TABLE IF EXISTS trading.exchange_exits")

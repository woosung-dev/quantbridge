"""add_orders_dispatch_snapshot

Revision ID: 20260503_0001
Revises: 20260425_0002
Create Date: 2026-05-03 14:30:00.000000

Sprint 23 BL-102 — `trading.orders.dispatch_snapshot` JSONB nullable 컬럼.
dispatch 시점 (exchange, mode, has_leverage) snapshot 저장. Sprint 22 BL-091
의 robustness 강화 — DB manual mutation / account.mode race 시에도 dispatch
일관성 보장.

schema: {"exchange": "bybit", "mode": "demo", "has_leverage": false}

nullable=True: legacy row (Sprint 23 이전 생성) 는 NULL → tasks/trading.py 의
fallback path (account 현재값 + Order.leverage) 자동 동작.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260503_0001"
down_revision = "20260425_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # conftest pre-create 가 이미 컬럼을 만들었을 수 있으므로 존재 확인 (idempotent).
    # 패턴 reference: 20260424_0002_add_backtest_idempotency_payload_hash.py
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='trading' AND table_name='orders' "
            "AND column_name='dispatch_snapshot'"
        )
    ).scalar()
    if existing:
        return
    op.add_column(
        "orders",
        sa.Column("dispatch_snapshot", JSONB(), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.drop_column("orders", "dispatch_snapshot", schema="trading")

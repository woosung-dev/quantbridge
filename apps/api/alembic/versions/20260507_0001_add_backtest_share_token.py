# 백테스트 share_token / share_revoked_at 컬럼 추가 — Sprint 41 Worker H
"""add_backtest_share_token

Revision ID: 20260507_0001
Revises: 20260505_0001
Create Date: 2026-05-07 21:00:00.000000

Sprint 41 Worker H — 백테스트 결과 외부 공유 link (public read-only + revoke).

schema:
- share_token: VARCHAR(64) nullable unique indexed — secrets.token_urlsafe(32) 결과
- share_revoked_at: TIMESTAMPTZ nullable — revoke 시점 (NULL = active)

nullable=True: 기존 row (share 미생성 backtest) 는 NULL.
unique + index: 토큰 lookup O(1) + 우연한 충돌 방지.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260507_0001"
down_revision = "20260505_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add share_token + share_revoked_at columns + unique index."""
    op.add_column(
        "backtests",
        sa.Column("share_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "backtests",
        sa.Column(
            "share_revoked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_backtests_share_token",
        "backtests",
        ["share_token"],
        unique=True,
    )


def downgrade() -> None:
    """Remove share columns + index."""
    op.drop_index("ix_backtests_share_token", table_name="backtests")
    op.drop_column("backtests", "share_revoked_at")
    op.drop_column("backtests", "share_token")

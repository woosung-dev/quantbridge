# LiveSignalSession 이 왜 종료됐는지를 영속화하는 컬럼을 추가하는 마이그레이션 (BL-484)
"""add live session deactivated reason

Revision ID: 20260730_0001
Revises: 20260728_0001
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0001"
down_revision = "20260728_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nullable — 이 마이그레이션 이전에 종료된 세션은 사유를 복원할 방법이 없다.
    # NULL 을 기본값으로 채우지 않는 이유: 없는 사유를 있는 것처럼 위장하지 않는다.
    # 값 집합은 src/trading/models.py 의 SessionDeactivationReason 이 정본 (PG enum 미사용 —
    # LiveSignalInterval 이 밟은 자동 enum cast 함정 회피 + 사유 추가에 DDL 불필요).
    op.add_column(
        "live_signal_sessions",
        sa.Column("deactivated_reason", sa.String(64), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.execute("ALTER TABLE trading.live_signal_sessions DROP COLUMN IF EXISTS deactivated_reason")

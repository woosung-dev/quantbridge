# LiveSignalState의 미사용 open trades snapshot 컬럼을 제거하는 마이그레이션
"""drop live signal state open trades snapshot

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260724_0002"
down_revision = "20260724_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS: 테스트 DB 는 conftest 가 metadata.create_all(신모델 — 컬럼 없음)로
    # 테이블을 재생성하는데 alembic_version(비모델 테이블)은 살아남아 stale revision
    # 에서 본 마이그레이션만 단독 실행될 수 있다 (20260626_0001 선례 미러).
    op.execute(
        "ALTER TABLE trading.live_signal_states DROP COLUMN IF EXISTS last_open_trades_snapshot"
    )


def downgrade() -> None:
    op.add_column(
        "live_signal_states",
        sa.Column(
            "last_open_trades_snapshot",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="trading",
    )

"""add_backtest_config_jsonb

Revision ID: 20260505_0001
Revises: 20260504_0002
Create Date: 2026-05-05 12:00:00.000000

Sprint 31 BL-162a — `backtests.config` JSONB nullable 컬럼 추가. TradingView
strategy 속성 패턴 (비용 시뮬레이션 + 마진) 사용자 입력값 저장.

schema: config = {"leverage": 1.0, "fees": 0.001, "slippage": 0.0005, "include_funding": true}

nullable=True: legacy row (Sprint 30 이전 backtest) 는 NULL → service
`_to_detail()` 가 engine BacktestConfig default 로 fallback (graceful degrade).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260505_0001"
down_revision = "20260504_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add config JSONB column (nullable, no backfill — service default fallback)."""
    op.add_column(
        "backtests",
        sa.Column("config", JSONB, nullable=True),
    )


def downgrade() -> None:
    """Remove config column."""
    op.drop_column("backtests", "config")

"""백테스트 실행 시 실제 입력 데이터 구간을 저장한다.

Revision ID: 20261021_0002
Revises: 20261021_0001
Create Date: 2026-10-21 00:02:00.000000

기존 행은 NULL로 유지하며 당시 입력 구간을 소급 추측하지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261021_0002"
down_revision: str | Sequence[str] | None = "20261021_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("data_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtests", "data_coverage")

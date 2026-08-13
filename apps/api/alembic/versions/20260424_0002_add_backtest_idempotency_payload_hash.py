"""add_backtest_idempotency_payload_hash

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24 00:00:01.000000

Sprint 9-6 E2 — `backtests.idempotency_payload_hash` BYTEA 컬럼. Same-key
+ different-body 충돌 감지용 SHA-256 hash. 기존 row (NULL) 는 어떤 body hash
와도 일치하지 않도록 처리 — 안전성 우선.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260424_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # conftest pre-create 가 이미 컬럼을 만들었을 수 있으므로 존재 확인.
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='backtests' "
            "AND column_name='idempotency_payload_hash'"
        )
    ).scalar()
    if existing:
        return
    op.add_column(
        "backtests",
        sa.Column("idempotency_payload_hash", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtests", "idempotency_payload_hash")

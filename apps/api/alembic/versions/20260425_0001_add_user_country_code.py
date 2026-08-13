"""add_user_country_code

Revision ID: 20260425_0001
Revises: 20260424_0002
Create Date: 2026-04-25 00:00:01.000000

Sprint 11 Phase A — `users.country_code` VARCHAR(2) 컬럼. Clerk webhook
public_metadata.country 에서 추출한 ISO 3166-1 alpha-2 코드. US/EU 27 + UK 는
Service 계층에서 차단. 기존 row 는 NULL (마이그레이션 호환).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260425_0001"
down_revision = "20260424_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # conftest pre-create 가 이미 컬럼을 만들었을 수 있으므로 존재 확인.
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='users' "
            "AND column_name='country_code'"
        )
    ).scalar()
    if existing:
        return
    op.add_column(
        "users",
        sa.Column("country_code", sa.String(length=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "country_code")

"""언어 중립 code_v1 snapshot을 기존 불변 StrategyVersion에 추가한다.

Revision ID: 20261022_0003
Revises: 20261022_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261022_0003"
down_revision: str | Sequence[str] | None = "20261022_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("strategies", "pine_source", nullable=True)
    op.alter_column("strategies", "pine_version", nullable=True)
    op.add_column(
        "strategies",
        sa.Column("source_language", sa.String(16), nullable=False, server_default="pine"),
    )
    op.add_column("strategies", sa.Column("execution_policy", sa.String(16), nullable=True))
    op.alter_column("strategy_versions", "pine_source", nullable=True)
    for column in (
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("source_code", sa.Text(), nullable=True),
        sa.Column("execution_policy", sa.String(16), nullable=True),
        sa.Column("warmup_bars", sa.Integer(), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=True),
        sa.Column("provenance", postgresql.JSONB(), nullable=True),
        sa.Column("execution_hash", sa.String(64), nullable=True),
    ):
        op.add_column("strategy_versions", column)


def downgrade() -> None:
    # code 행을 가짜 Pine로 되돌리거나 삭제하는 downgrade는 허용하지 않는다.
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT count(*) FROM strategies WHERE execution_policy IS NOT NULL")
    ).scalar_one():
        raise RuntimeError("code_v1 전략이 있어 손실 없는 downgrade가 불가능합니다")
    for name in (
        "execution_hash",
        "provenance",
        "params",
        "warmup_bars",
        "execution_policy",
        "source_code",
        "language",
    ):
        op.drop_column("strategy_versions", name)
    op.alter_column("strategy_versions", "pine_source", nullable=False)
    op.drop_column("strategies", "execution_policy")
    op.drop_column("strategies", "source_language")
    op.alter_column("strategies", "pine_version", nullable=False)
    op.alter_column("strategies", "pine_source", nullable=False)

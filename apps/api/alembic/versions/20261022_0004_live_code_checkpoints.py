"""재시작 가능한 코드 봉 입력·관찰 포지션·의도 체크포인트.

Revision ID: 20261022_0004
Revises: 20261022_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261022_0004"
down_revision: str | Sequence[str] | None = "20261022_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_code_bars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trading.live_signal_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("bar_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("execution_hash", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("bar", postgresql.JSONB(), nullable=False),
        sa.Column("position", postgresql.JSONB(), nullable=False),
        sa.Column("delivery_args", postgresql.JSONB(), nullable=False),
        sa.Column("intent", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("is_warmup", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("session_id", "bar_time", name="uq_live_code_bars_session_time"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_live_code_bars_session_sequence"),
        sa.CheckConstraint(
            "status IN ('warmup','prepared','delivered','blocked')", name="ck_live_code_bars_status"
        ),
        schema="trading",
    )
    op.create_index(
        "ix_trading_live_code_bars_session_id", "live_code_bars", ["session_id"], schema="trading"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trading_live_code_bars_session_id", table_name="live_code_bars", schema="trading"
    )
    op.drop_table("live_code_bars", schema="trading")

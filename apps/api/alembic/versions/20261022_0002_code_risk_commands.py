"""고정 리스크 명령의 lease·멱등 outbox."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261022_0002"
down_revision: str | Sequence[str] | None = "20261022_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "live_signal_sessions",
        sa.Column("strategy_version_id", sa.Uuid(), nullable=True),
        schema="trading",
    )
    op.create_foreign_key(
        "fk_live_sessions_strategy_version",
        "live_signal_sessions",
        "strategy_versions",
        ["strategy_version_id"],
        ["id"],
        source_schema="trading",
        ondelete="RESTRICT",
    )
    op.create_table(
        "code_risk_commands",
        sa.Column("key", sa.String(240), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','applied','failed','superseded')",
            name="ck_code_risk_command_status",
        ),
        schema="trading",
    )
    op.create_index(
        "ix_code_risk_commands_pending",
        "code_risk_commands",
        ["session_id", "status"],
        schema="trading",
    )


def downgrade() -> None:
    op.drop_table("code_risk_commands", schema="trading")
    op.drop_constraint(
        "fk_live_sessions_strategy_version",
        "live_signal_sessions",
        schema="trading",
        type_="foreignkey",
    )
    op.drop_column("live_signal_sessions", "strategy_version_id", schema="trading")

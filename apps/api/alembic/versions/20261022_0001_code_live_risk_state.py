"""코드 전략의 세대별 체결·보호 원장. 기존 세션과 주문은 NULL 계약을 유지한다."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261022_0001"
down_revision: str | Sequence[str] | None = "20261021_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("risk_context", postgresql.JSONB(), nullable=True), schema="trading"
    )
    op.add_column(
        "live_signal_sessions",
        sa.Column("execution_snapshot", postgresql.JSONB(), nullable=True),
        schema="trading",
    )
    op.create_table(
        "live_risk_states",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("direction", sa.String(5), nullable=False),
        sa.Column(
            "entry_order_id",
            sa.Uuid(),
            sa.ForeignKey("trading.orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *[
            sa.Column(name, sa.Numeric(18, 8), nullable=False)
            for name in ("expected_quantity", "qty_step", "min_qty", "provisional_stop")
        ],
        *[
            sa.Column(name, sa.Numeric(18, 8), nullable=False, server_default="0")
            for name in ("cumulative_quantity", "position_quantity", "tp_filled_quantity")
        ],
        sa.Column("cumulative_value", sa.Numeric(28, 8), nullable=False, server_default="0"),
        *[sa.Column(name, sa.Numeric(18, 8), nullable=True) for name in ("entry_vwap", "fixed_r")],
        sa.Column("reference_bars", postgresql.JSONB(), nullable=False),
        *[
            sa.Column(
                name, postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
            )
            for name in ("protection_desired", "protection_applied", "exit_fills")
        ],
        *[
            sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.text("false"))
            for name in (
                "entry_terminal",
                "trailing_active",
                "close_requested",
                "cancels_confirmed",
                "new_entries_blocked",
            )
        ],
        sa.Column("pending_reversal", sa.String(5), nullable=True),
        sa.Column("failure_reason", sa.String(200), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("revision >= 0 AND generation >= 1", name="ck_live_risk_revision"),
        sa.CheckConstraint(
            "cumulative_quantity >= 0 AND cumulative_value >= 0 AND position_quantity >= 0 AND tp_filled_quantity >= 0 AND expected_quantity > 0 AND qty_step > 0 AND min_qty > 0",
            name="ck_live_risk_quantities",
        ),
        sa.CheckConstraint("fixed_r IS NULL OR fixed_r > 0", name="ck_live_risk_fixed_r"),
        sa.CheckConstraint("direction IN ('long','short')", name="ck_live_risk_direction"),
        schema="trading",
    )


def downgrade() -> None:
    op.drop_table("live_risk_states", schema="trading")
    op.drop_column("live_signal_sessions", "execution_snapshot", schema="trading")
    op.drop_column("orders", "risk_context", schema="trading")

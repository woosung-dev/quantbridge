"""미귀속 native 청산의 미정산 수량을 새 진입 가드에 영속한다."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261022_0005"
down_revision: str | Sequence[str] | None = "20261022_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "live_risk_states_session_id_fkey", "live_risk_states", schema="trading", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_live_risk_states_session_id",
        "live_risk_states",
        "live_signal_sessions",
        ["session_id"],
        ["id"],
        source_schema="trading",
        referent_schema="trading",
        ondelete="RESTRICT",
    )
    op.add_column(
        "live_risk_states",
        sa.Column("unsettled_exit_quantity", sa.Numeric(18, 8), nullable=False, server_default="0"),
        schema="trading",
    )
    op.create_check_constraint(
        "ck_live_risk_unsettled_exit",
        "live_risk_states",
        "unsettled_exit_quantity >= 0",
        schema="trading",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_live_risk_states_session_id", "live_risk_states", schema="trading", type_="foreignkey"
    )
    op.create_foreign_key(
        "live_risk_states_session_id_fkey",
        "live_risk_states",
        "live_signal_sessions",
        ["session_id"],
        ["id"],
        source_schema="trading",
        referent_schema="trading",
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "ck_live_risk_unsettled_exit", "live_risk_states", schema="trading", type_="check"
    )
    op.drop_column("live_risk_states", "unsettled_exit_quantity", schema="trading")

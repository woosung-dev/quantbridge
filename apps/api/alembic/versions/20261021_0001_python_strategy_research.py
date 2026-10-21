"""Python 연구 전략·불변 버전·백테스트 원장. 기존 Pine 테이블은 변경하지 않는다."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261021_0001"
down_revision: str | Sequence[str] | None = "20261002_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "python_strategies",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_python_strategies_user_id", "python_strategies", ["user_id"])
    op.create_table(
        "python_strategy_versions",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "strategy_id",
            sa.Uuid(),
            sa.ForeignKey("python_strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("warmup_bars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_python_strategy_versions_strategy_id", "python_strategy_versions", ["strategy_id"]
    )
    op.create_foreign_key(
        "fk_python_strategy_current_version",
        "python_strategies",
        "python_strategy_versions",
        ["version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "python_backtests",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "strategy_id",
            sa.Uuid(),
            sa.ForeignKey("python_strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("python_strategy_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed','cancelled')",
            name="ck_python_backtest_status",
        ),
    )
    op.create_index("ix_python_backtests_user_id", "python_backtests", ["user_id"])
    op.create_index("ix_python_backtests_strategy_id", "python_backtests", ["strategy_id"])


def downgrade() -> None:
    op.drop_table("python_backtests")
    op.drop_constraint(
        "fk_python_strategy_current_version", "python_strategies", type_="foreignkey"
    )
    op.drop_table("python_strategy_versions")
    op.drop_table("python_strategies")

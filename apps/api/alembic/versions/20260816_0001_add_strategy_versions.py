"""add immutable strategy versions for backtest reproducibility

기존 Backtest의 실행 당시 source는 복원할 수 없다. 따라서 각 Strategy의 현재 source로
StrategyVersion 하나를 만들고 모든 Backtest를 그 snapshot에 연결한다. 이는 과거 실행을
재현했다는 주장이 아니라, 이후 source 변경이 과거 결과의 실행 입력을 바꾸지 못하게 하는
기준선을 만든다는 뜻이다.

Revision ID: 20260816_0001
Revises: 20260817_0001
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260816_0001"
down_revision: str | Sequence[str] | None = "20260817_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARSER_VERSION = "pine_v2"


def upgrade() -> None:
    op.create_table(
        "strategy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pine_source", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])
    op.create_index(
        "ix_strategy_versions_strategy_created",
        "strategy_versions",
        ["strategy_id", "created_at"],
    )

    op.add_column(
        "strategies",
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_strategies_strategy_version_id", "strategies", ["strategy_version_id"])
    op.create_foreign_key(
        "fk_strategies_strategy_version_id_strategy_versions",
        "strategies",
        "strategy_versions",
        ["strategy_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "backtests",
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("backtests", sa.Column("engine_version", sa.String(length=32), nullable=True))
    op.create_index("ix_backtests_strategy_version_id", "backtests", ["strategy_version_id"])
    op.create_foreign_key(
        "fk_backtests_strategy_version_id_strategy_versions",
        "backtests",
        "strategy_versions",
        ["strategy_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    bind = op.get_bind()
    strategies = bind.execute(
        sa.text("SELECT id, pine_source, created_at FROM strategies")
    ).mappings()
    for strategy in strategies:
        source = strategy["pine_source"]
        version_id = uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO strategy_versions "
                "(id, strategy_id, pine_source, source_hash, parser_version, created_at) "
                "VALUES (:id, :strategy_id, :pine_source, :source_hash, :parser_version, :created_at)"
            ),
            {
                "id": version_id,
                "strategy_id": strategy["id"],
                "pine_source": source,
                "source_hash": hashlib.sha256(source.encode()).hexdigest(),
                "parser_version": _PARSER_VERSION,
                "created_at": strategy["created_at"],
            },
        )
        bind.execute(
            sa.text(
                "UPDATE strategies SET strategy_version_id = :version_id WHERE id = :strategy_id"
            ),
            {"version_id": version_id, "strategy_id": strategy["id"]},
        )

    bind.execute(
        sa.text(
            "UPDATE backtests SET strategy_version_id = strategies.strategy_version_id "
            "FROM strategies WHERE backtests.strategy_id = strategies.id"
        )
    )
    missing = bind.execute(
        sa.text("SELECT count(*) FROM backtests WHERE strategy_version_id IS NULL")
    ).scalar_one()
    if missing:
        raise RuntimeError(f"strategy_versions backfill left {missing} backtests unpinned")


def downgrade() -> None:
    op.drop_constraint(
        "fk_backtests_strategy_version_id_strategy_versions",
        "backtests",
        type_="foreignkey",
    )
    op.drop_index("ix_backtests_strategy_version_id", table_name="backtests")
    op.drop_column("backtests", "engine_version")
    op.drop_column("backtests", "strategy_version_id")

    op.drop_constraint(
        "fk_strategies_strategy_version_id_strategy_versions",
        "strategies",
        type_="foreignkey",
    )
    op.drop_index("ix_strategies_strategy_version_id", table_name="strategies")
    op.drop_column("strategies", "strategy_version_id")

    op.drop_index("ix_strategy_versions_strategy_created", table_name="strategy_versions")
    op.drop_index("ix_strategy_versions_strategy_id", table_name="strategy_versions")
    op.drop_table("strategy_versions")

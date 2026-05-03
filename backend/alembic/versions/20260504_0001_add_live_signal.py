"""add_live_signal_sessions_states_events_and_strategy_settings

Revision ID: 20260504_0001
Revises: 20260503_0001
Create Date: 2026-05-04 09:00:00.000000

Sprint 26 — Pine Signal Auto-Trading.

신규 컬럼/테이블:
- `strategies.settings` JSONB nullable — Live Signal 의 trading params
  (StrategySettings: leverage / margin_mode / position_size_pct + schema_version).
  None = unset (Live Signal 시작 차단). codex G.0 P2 #4 — read path validate.

- `trading.live_signal_sessions` — Pine evaluate + broker 발주 session.
  Partial unique index on (user_id, strategy_id, exchange_account_id, symbol)
  WHERE is_active = true (codex G.0 P2 #2 — deactivate 후 재INSERT 허용).

- `trading.live_signal_states` — 1:1 with sessions, ON DELETE CASCADE.
  Option B (warmup replay) 채택 — UI/디버깅 캐시 용도. schema_version 명시.

- `trading.live_signal_events` — Transactional outbox (codex G.0 P1 #3).
  UNIQUE (session_id, bar_time, sequence_no, action, trade_id) — idempotency.
  Partial pending index — list_pending 빠른 조회.

Idempotent guards: 모든 add 가 information_schema 검사 후 진행.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260504_0001"
down_revision = "20260503_0001"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str, schema: str = "public") -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema=:schema AND table_name=:table AND column_name=:column"
            ),
            {"schema": schema, "table": table, "column": column},
        ).scalar()
    )


def _table_exists(table: str, schema: str = "public") -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema=:schema AND table_name=:table"
            ),
            {"schema": schema, "table": table},
        ).scalar()
    )


def _index_exists(index_name: str, schema: str = "public") -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE schemaname=:schema AND indexname=:index"),
            {"schema": schema, "index": index_name},
        ).scalar()
    )


def upgrade() -> None:
    # 1. strategies.settings JSONB
    if not _column_exists("strategies", "settings"):
        op.add_column(
            "strategies",
            sa.Column("settings", JSONB(), nullable=True),
        )

    # 2. trading.live_signal_sessions
    if not _table_exists("live_signal_sessions", schema="trading"):
        op.create_table(
            "live_signal_sessions",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "strategy_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("strategies.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "exchange_account_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("trading.exchange_accounts.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("symbol", sa.String(32), nullable=False),
            sa.Column("interval", sa.String(8), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("last_evaluated_bar_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("bar_claim_token", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
            schema="trading",
        )
    if not _index_exists("ix_live_sessions_user_active", schema="trading"):
        op.create_index(
            "ix_live_sessions_user_active",
            "live_signal_sessions",
            ["user_id", "is_active"],
            schema="trading",
        )
    if not _index_exists("ix_live_sessions_active_due", schema="trading"):
        op.create_index(
            "ix_live_sessions_active_due",
            "live_signal_sessions",
            ["is_active", "last_evaluated_bar_time"],
            postgresql_where=sa.text("is_active = true"),
            schema="trading",
        )
    if not _index_exists("uq_live_sessions_active_unique", schema="trading"):
        # P2 #2: partial unique — is_active=true 인 row 만 unique. deactivate 후 재INSERT 허용.
        op.create_index(
            "uq_live_sessions_active_unique",
            "live_signal_sessions",
            ["user_id", "strategy_id", "exchange_account_id", "symbol"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
            schema="trading",
        )

    # 3. trading.live_signal_states (1:1 with sessions)
    if not _table_exists("live_signal_states", schema="trading"):
        op.create_table(
            "live_signal_states",
            sa.Column(
                "session_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column(
                "last_strategy_state_report",
                JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "last_open_trades_snapshot",
                JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "total_closed_trades", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column(
                "total_realized_pnl",
                sa.Numeric(18, 8),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            schema="trading",
        )

    # 4. trading.live_signal_events (Transactional outbox)
    if not _table_exists("live_signal_events", schema="trading"):
        op.create_table(
            "live_signal_events",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "session_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("bar_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sequence_no", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(16), nullable=False),
            sa.Column("direction", sa.String(8), nullable=False),
            sa.Column("trade_id", sa.String(64), nullable=False),
            sa.Column("qty", sa.Numeric(18, 8), nullable=False),
            sa.Column("comment", sa.String(200), nullable=False, server_default=sa.text("''")),
            sa.Column(
                "status",
                sa.String(16),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column(
                "order_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("trading.orders.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("error_message", sa.String(2000), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "session_id",
                "bar_time",
                "sequence_no",
                "action",
                "trade_id",
                name="uq_live_signal_events_idempotency",
            ),
            schema="trading",
        )
    if not _index_exists("ix_live_signal_events_session_bar", schema="trading"):
        op.create_index(
            "ix_live_signal_events_session_bar",
            "live_signal_events",
            ["session_id", "bar_time"],
            schema="trading",
        )
    if not _index_exists("ix_live_signal_events_pending", schema="trading"):
        op.create_index(
            "ix_live_signal_events_pending",
            "live_signal_events",
            ["status"],
            postgresql_where=sa.text("status = 'pending'"),
            schema="trading",
        )


def downgrade() -> None:
    # 역순 drop
    op.drop_index(
        "ix_live_signal_events_pending", table_name="live_signal_events", schema="trading"
    )
    op.drop_index(
        "ix_live_signal_events_session_bar", table_name="live_signal_events", schema="trading"
    )
    op.drop_table("live_signal_events", schema="trading")

    op.drop_table("live_signal_states", schema="trading")

    op.drop_index(
        "uq_live_sessions_active_unique", table_name="live_signal_sessions", schema="trading"
    )
    op.drop_index(
        "ix_live_sessions_active_due", table_name="live_signal_sessions", schema="trading"
    )
    op.drop_index(
        "ix_live_sessions_user_active", table_name="live_signal_sessions", schema="trading"
    )
    op.drop_table("live_signal_sessions", schema="trading")

    # strategies.settings 는 데이터 손실 우려 — drop 자동, 백업은 수동.
    op.drop_column("strategies", "settings")

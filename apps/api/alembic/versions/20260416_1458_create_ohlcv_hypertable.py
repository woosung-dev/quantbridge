"""create_ohlcv_hypertable

Revision ID: cdecaaed829b
Revises: 7beabad6be77
Create Date: 2026-04-16 14:58:05.584279

ts.ohlcv 일반 테이블 생성 후 TimescaleDB hypertable로 변환 (7일 chunk).
ts schema는 docker/db/init/01-timescaledb.sql에서 사전 생성됨.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cdecaaed829b"
down_revision: str | Sequence[str] | None = "7beabad6be77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0. 마이그레이션 자체가 ts schema + timescaledb extension 의존성을 책임진다.
    #    docker/db/init/01-timescaledb.sql과 중복이지만 idempotent하므로 안전.
    #    (test DB / fresh DB 모두 init SQL 미적용 가능 → 마이그레이션 단독 동작 보장)
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    op.execute("CREATE SCHEMA IF NOT EXISTS ts;")

    # 1. 일반 테이블 생성 (ts schema)
    op.create_table(
        "ohlcv",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("open", sa.Numeric(18, 8), nullable=False),
        sa.Column("high", sa.Numeric(18, 8), nullable=False),
        sa.Column("low", sa.Numeric(18, 8), nullable=False),
        sa.Column("close", sa.Numeric(18, 8), nullable=False),
        sa.Column("volume", sa.Numeric(18, 8), nullable=False),
        sa.PrimaryKeyConstraint("time", "symbol", "timeframe"),
        schema="ts",
    )
    op.create_index(
        "ix_ohlcv_symbol_tf_time_desc",
        "ohlcv",
        ["symbol", "timeframe", "time"],
        schema="ts",
    )

    # 2. hypertable 변환 — chunk 7일 단위
    op.execute(
        "SELECT create_hypertable('ts.ohlcv', 'time', "
        "chunk_time_interval => INTERVAL '7 days', "
        "if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.drop_index("ix_ohlcv_symbol_tf_time_desc", table_name="ohlcv", schema="ts")
    op.drop_table("ohlcv", schema="ts")

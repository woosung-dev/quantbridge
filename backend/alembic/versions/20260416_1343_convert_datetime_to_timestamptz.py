"""convert datetime to timestamptz

WARNING: ALTER COLUMN TYPE TIMESTAMPTZ 는 ACCESS EXCLUSIVE lock 사용.
현재 테이블은 작아서 무영향. 향후 대용량 테이블(예: backtest_trades, ohlcv)에
동일 패턴 적용 금지 — pg_repack 등 별도 전략 필요.

대상 컬럼 (9개):
- users.created_at, users.updated_at
- strategies.created_at, strategies.updated_at
- backtests.created_at, backtests.started_at, backtests.completed_at
- backtest_trades.entry_time, backtest_trades.exit_time

USING ... AT TIME ZONE 'UTC' 로 기존 naive datetime 값을 UTC 로 해석.
(NULL 값은 그대로 보존. nullable=True 컬럼이어도 ALTER COLUMN TYPE 적용 가능.)

T3 의 AwareDateTime TypeDecorator 와 DB schema 를 정합시키는 migration.

Revision ID: 7beabad6be77
Revises: 882849301c63
Create Date: 2026-04-16 13:43:52.702770

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7beabad6be77'
down_revision: str | Sequence[str] | None = '882849301c63'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMPTZ "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    # strategies
    op.execute(
        "ALTER TABLE strategies ALTER COLUMN created_at TYPE TIMESTAMPTZ "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE strategies ALTER COLUMN updated_at TYPE TIMESTAMPTZ "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    # backtests
    op.execute(
        "ALTER TABLE backtests ALTER COLUMN created_at TYPE TIMESTAMPTZ "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtests ALTER COLUMN started_at TYPE TIMESTAMPTZ "
        "USING started_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtests ALTER COLUMN completed_at TYPE TIMESTAMPTZ "
        "USING completed_at AT TIME ZONE 'UTC'"
    )
    # backtest_trades
    op.execute(
        "ALTER TABLE backtest_trades ALTER COLUMN entry_time TYPE TIMESTAMPTZ "
        "USING entry_time AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtest_trades ALTER COLUMN exit_time TYPE TIMESTAMPTZ "
        "USING exit_time AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    # 역방향: TIMESTAMPTZ → TIMESTAMP (UTC 기준 strip)
    # upgrade 순서의 역순으로 적용
    op.execute(
        "ALTER TABLE backtest_trades ALTER COLUMN exit_time TYPE TIMESTAMP "
        "USING exit_time AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtest_trades ALTER COLUMN entry_time TYPE TIMESTAMP "
        "USING entry_time AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtests ALTER COLUMN completed_at TYPE TIMESTAMP "
        "USING completed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtests ALTER COLUMN started_at TYPE TIMESTAMP "
        "USING started_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE backtests ALTER COLUMN created_at TYPE TIMESTAMP "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE strategies ALTER COLUMN updated_at TYPE TIMESTAMP "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE strategies ALTER COLUMN created_at TYPE TIMESTAMP "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMP "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP "
        "USING created_at AT TIME ZONE 'UTC'"
    )

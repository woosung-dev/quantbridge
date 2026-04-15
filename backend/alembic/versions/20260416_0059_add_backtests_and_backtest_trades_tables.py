"""add backtests and backtest_trades tables

Revision ID: 882849301c63
Revises: 8bfdc01a6094
Create Date: 2026-04-16 00:59:01.012921

NOTE:
- backtest_status: 6개 값 (QUEUED, RUNNING, CANCELLING, COMPLETED, FAILED, CANCELLED)
  CANCELLING 은 transient — Worker 3-guard 가 CANCELLED 로 최종 전이
- FK 정책:
  user_id     → users.id      ondelete='CASCADE'   (유저 삭제 시 백테스트도 삭제)
  strategy_id → strategies.id ondelete='RESTRICT'  (전략 삭제 시 백테스트 보호)
  backtest_id → backtests.id  ondelete='CASCADE'   (백테스트 삭제 시 거래 내역도 삭제)
- error 컬럼: TEXT (unbounded — vectorbt stacktrace 저장 목적)
- metrics, equity_curve: JSONB
- ENUM 생성: create_type=False + DO $$ BEGIN ... END $$ 블록으로 idempotent 처리
  (strategy migration 동일 패턴 — PostgreSQL CREATE TYPE IF NOT EXISTS 미지원 회피)
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '882849301c63'
down_revision: str | Sequence[str] | None = '8bfdc01a6094'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ENUM 타입을 명시적으로 생성 (create_type=False 로 테이블 생성 시 자동 생성 방지)
    # PostgreSQL 은 CREATE TYPE IF NOT EXISTS 를 지원하지 않으므로 DO 블록으로 처리
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE backtest_status AS ENUM (
                'QUEUED', 'RUNNING', 'CANCELLING', 'COMPLETED', 'FAILED', 'CANCELLED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE trade_direction AS ENUM ('LONG', 'SHORT');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE trade_status AS ENUM ('OPEN', 'CLOSED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        'backtests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('timeframe', sqlmodel.sql.sqltypes.AutoString(length=8), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'QUEUED', 'RUNNING', 'CANCELLING', 'COMPLETED', 'FAILED', 'CANCELLED',
                name='backtest_status',
                create_type=False,  # DO $$ 블록으로 이미 생성
            ),
            nullable=False,
        ),
        sa.Column('celery_task_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('equity_curve', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_backtests_status', 'backtests', ['status'], unique=False)
    op.create_index(op.f('ix_backtests_strategy_id'), 'backtests', ['strategy_id'], unique=False)
    op.create_index('ix_backtests_user_created', 'backtests', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_backtests_user_id'), 'backtests', ['user_id'], unique=False)

    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('backtest_id', sa.Uuid(), nullable=False),
        sa.Column('trade_index', sa.Integer(), nullable=False),
        sa.Column(
            'direction',
            postgresql.ENUM('LONG', 'SHORT', name='trade_direction', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'status',
            postgresql.ENUM('OPEN', 'CLOSED', name='trade_status', create_type=False),
            nullable=False,
        ),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('entry_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('exit_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('size', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('pnl', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('return_pct', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('fees', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_backtest_trades_backtest_id'), 'backtest_trades', ['backtest_id'], unique=False)
    op.create_index('ix_backtest_trades_backtest_idx', 'backtest_trades', ['backtest_id', 'trade_index'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_backtest_trades_backtest_idx', table_name='backtest_trades')
    op.drop_index(op.f('ix_backtest_trades_backtest_id'), table_name='backtest_trades')
    op.drop_table('backtest_trades')
    op.drop_index(op.f('ix_backtests_user_id'), table_name='backtests')
    op.drop_index('ix_backtests_user_created', table_name='backtests')
    op.drop_index(op.f('ix_backtests_strategy_id'), table_name='backtests')
    op.drop_index('ix_backtests_status', table_name='backtests')
    op.drop_table('backtests')
    # ENUM 타입은 테이블 drop 후에 명시적으로 삭제해야 함
    # (Alembic autogenerate 는 ENUM drop 을 생략하는 경우가 있어 수동 추가)
    op.execute("DROP TYPE IF EXISTS trade_status")
    op.execute("DROP TYPE IF EXISTS trade_direction")
    op.execute("DROP TYPE IF EXISTS backtest_status")

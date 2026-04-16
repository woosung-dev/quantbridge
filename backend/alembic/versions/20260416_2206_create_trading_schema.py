"""create trading schema

Revision ID: faa9ad7b4585
Revises: cdecaaed829b
Create Date: 2026-04-16 22:06:21.325132

Sprint 6 T2 — trading 스키마 + 4 테이블 (exchange_accounts, orders,
kill_switch_events, webhook_secrets) 생성.

NOTE:
- autogenerate가 감지한 ts.ohlcv 블록은 제거됨. 원인: T1 모델의
  AwareDateTime 타입과 cdecaaed829b 의 sa.DateTime(timezone=True) 사이
  compare_type drift. T2 scope가 아니므로 별도 과제로 defer.
- FK ondelete 정책:
  - exchange_accounts.user_id → users.id CASCADE
  - orders.strategy_id → strategies.id RESTRICT (진행 중 주문 보호)
  - orders.exchange_account_id → trading.exchange_accounts.id RESTRICT
  - kill_switch_events.strategy_id / exchange_account_id → CASCADE
  - webhook_secrets.strategy_id → strategies.id CASCADE
- Partial indexes:
  - uq_orders_idempotency_key: WHERE idempotency_key IS NOT NULL
  - ix_kill_switch_events_active_*: WHERE resolved_at IS NULL
- CHECK 제약: ck_kill_switch_events_trigger_scope — trigger_type별
  strategy_id/exchange_account_id XOR 강제.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op
from src.common.datetime_types import AwareDateTime

# revision identifiers, used by Alembic.
revision: str = 'faa9ad7b4585'
down_revision: str | Sequence[str] | None = 'cdecaaed829b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # trading schema를 명시적으로 생성 (autogenerate는 CREATE SCHEMA 생략)
    op.execute("CREATE SCHEMA IF NOT EXISTS trading")

    # ENUM 타입을 명시적으로 생성 (create_type=False 로 테이블 생성 시 자동 생성 방지).
    # PostgreSQL 은 CREATE TYPE IF NOT EXISTS 를 지원하지 않으므로 DO 블록으로 idempotent.
    # backtest migration과 동일 패턴.
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE exchangename AS ENUM ('bybit', 'binance');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE exchangemode AS ENUM ('demo', 'testnet', 'live');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE killswitchtriggertype AS ENUM (
                'cumulative_loss', 'daily_loss', 'api_error'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE orderside AS ENUM ('buy', 'sell');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE ordertype AS ENUM ('market', 'limit');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE orderstate AS ENUM (
                'pending', 'submitted', 'filled', 'rejected', 'cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        'exchange_accounts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column(
            'exchange',
            postgresql.ENUM('bybit', 'binance', name='exchangename', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'mode',
            postgresql.ENUM(
                'demo', 'testnet', 'live', name='exchangemode', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('api_key_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('api_secret_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('label', sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True),
        sa.Column(
            'created_at',
            AwareDateTime(),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            AwareDateTime(),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='trading',
    )
    op.create_index(
        'ix_exchange_accounts_user',
        'exchange_accounts',
        ['user_id'],
        unique=False,
        schema='trading',
    )

    op.create_table(
        'kill_switch_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column(
            'trigger_type',
            postgresql.ENUM(
                'cumulative_loss',
                'daily_loss',
                'api_error',
                name='killswitchtriggertype',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('strategy_id', sa.Uuid(), nullable=True),
        sa.Column('exchange_account_id', sa.Uuid(), nullable=True),
        sa.Column('trigger_value', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('threshold', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column(
            'triggered_at',
            AwareDateTime(),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column('resolved_at', AwareDateTime(), nullable=True),
        sa.Column(
            'resolution_note',
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(trigger_type = 'cumulative_loss' AND strategy_id IS NOT NULL AND exchange_account_id IS NULL) "
            "OR (trigger_type IN ('daily_loss','api_error')     "
            "AND exchange_account_id IS NOT NULL AND strategy_id IS NULL)",
            name='ck_kill_switch_events_trigger_scope',
        ),
        sa.ForeignKeyConstraint(
            ['exchange_account_id'],
            ['trading.exchange_accounts.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['strategy_id'],
            ['strategies.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='trading',
    )
    op.create_index(
        'ix_kill_switch_events_active_account',
        'kill_switch_events',
        ['exchange_account_id'],
        unique=False,
        schema='trading',
        postgresql_where=sa.text('resolved_at IS NULL'),
    )
    op.create_index(
        'ix_kill_switch_events_active_strategy',
        'kill_switch_events',
        ['strategy_id'],
        unique=False,
        schema='trading',
        postgresql_where=sa.text('resolved_at IS NULL'),
    )

    op.create_table(
        'orders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('exchange_account_id', sa.Uuid(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column(
            'side',
            postgresql.ENUM('buy', 'sell', name='orderside', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'type',
            postgresql.ENUM('market', 'limit', name='ordertype', create_type=False),
            nullable=False,
        ),
        sa.Column('quantity', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column(
            'state',
            postgresql.ENUM(
                'pending',
                'submitted',
                'filled',
                'rejected',
                'cancelled',
                name='orderstate',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('webhook_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            'idempotency_key',
            sqlmodel.sql.sqltypes.AutoString(length=200),
            nullable=True,
        ),
        sa.Column(
            'exchange_order_id',
            sqlmodel.sql.sqltypes.AutoString(length=120),
            nullable=True,
        ),
        sa.Column('filled_price', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('filled_quantity', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('realized_pnl', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('idempotency_payload_hash', sa.LargeBinary(), nullable=True),
        sa.Column(
            'error_message',
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
        sa.Column('submitted_at', AwareDateTime(), nullable=True),
        sa.Column('filled_at', AwareDateTime(), nullable=True),
        sa.Column(
            'created_at',
            AwareDateTime(),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            AwareDateTime(),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['exchange_account_id'],
            ['trading.exchange_accounts.id'],
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['strategy_id'],
            ['strategies.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='trading',
    )
    op.create_index(
        'ix_orders_account_state',
        'orders',
        ['exchange_account_id', 'state'],
        unique=False,
        schema='trading',
    )
    op.create_index(
        'ix_orders_strategy',
        'orders',
        ['strategy_id'],
        unique=False,
        schema='trading',
    )
    # state 컬럼 단독 index (Field(index=True) 자동 생성 — drift 검증 통과용)
    op.create_index(
        op.f('ix_trading_orders_state'),
        'orders',
        ['state'],
        unique=False,
        schema='trading',
    )
    op.create_index(
        'uq_orders_idempotency_key',
        'orders',
        ['idempotency_key'],
        unique=True,
        schema='trading',
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )

    op.create_table(
        'webhook_secrets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('secret_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column(
            'created_at',
            AwareDateTime(),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column('revoked_at', AwareDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['strategy_id'],
            ['strategies.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='trading',
    )
    op.create_index(
        'ix_webhook_secrets_strategy_active',
        'webhook_secrets',
        ['strategy_id', 'revoked_at'],
        unique=False,
        schema='trading',
    )


def downgrade() -> None:
    op.drop_index(
        'ix_webhook_secrets_strategy_active',
        table_name='webhook_secrets',
        schema='trading',
    )
    op.drop_table('webhook_secrets', schema='trading')
    op.drop_index(
        'uq_orders_idempotency_key',
        table_name='orders',
        schema='trading',
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )
    op.drop_index(
        op.f('ix_trading_orders_state'),
        table_name='orders',
        schema='trading',
    )
    op.drop_index('ix_orders_strategy', table_name='orders', schema='trading')
    op.drop_index('ix_orders_account_state', table_name='orders', schema='trading')
    op.drop_table('orders', schema='trading')
    op.drop_index(
        'ix_kill_switch_events_active_strategy',
        table_name='kill_switch_events',
        schema='trading',
        postgresql_where=sa.text('resolved_at IS NULL'),
    )
    op.drop_index(
        'ix_kill_switch_events_active_account',
        table_name='kill_switch_events',
        schema='trading',
        postgresql_where=sa.text('resolved_at IS NULL'),
    )
    op.drop_table('kill_switch_events', schema='trading')
    op.drop_index(
        'ix_exchange_accounts_user',
        table_name='exchange_accounts',
        schema='trading',
    )
    op.drop_table('exchange_accounts', schema='trading')

    # ENUM 타입 명시적 삭제 (Alembic autogenerate 누락 패턴 — backtest migration 동일)
    op.execute("DROP TYPE IF EXISTS orderstate")
    op.execute("DROP TYPE IF EXISTS ordertype")
    op.execute("DROP TYPE IF EXISTS orderside")
    op.execute("DROP TYPE IF EXISTS killswitchtriggertype")
    op.execute("DROP TYPE IF EXISTS exchangemode")
    op.execute("DROP TYPE IF EXISTS exchangename")

    op.execute("DROP SCHEMA IF EXISTS trading CASCADE")

"""trading 도메인 SQLModel 테이블. Sprint 6.

Schema: 모두 `trading` 스키마 격리 (Sprint 5 ts schema 패턴).
DateTime: AwareDateTime + TIMESTAMPTZ 강제 (ADR-005).
Decimal: 금액/수량은 NUMERIC(18, 8) — Sprint 4 D8 교훈.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, LargeBinary, SQLModel

from src.common.datetime_types import AwareDateTime


class ExchangeName(StrEnum):
    bybit = "bybit"
    binance = "binance"  # Sprint 7+


class ExchangeMode(StrEnum):
    demo = "demo"
    testnet = "testnet"
    live = "live"  # Sprint 7+


class OrderSide(StrEnum):
    buy = "buy"
    sell = "sell"


class OrderType(StrEnum):
    market = "market"
    limit = "limit"


class OrderState(StrEnum):
    pending = "pending"
    submitted = "submitted"
    filled = "filled"
    rejected = "rejected"
    cancelled = "cancelled"


class KillSwitchTriggerType(StrEnum):
    # autoplan CEO F4: "cumulative_loss"는 peak-based drawdown이 아니므로 semantic-correct naming 사용
    cumulative_loss = "cumulative_loss"
    daily_loss = "daily_loss"
    api_error = "api_error"


class ExchangeAccount(SQLModel, table=True):
    __tablename__ = "exchange_accounts"
    __table_args__ = (
        Index("ix_exchange_accounts_user", "user_id"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    exchange: ExchangeName = Field(nullable=False)
    mode: ExchangeMode = Field(nullable=False)
    api_key_encrypted: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    api_secret_encrypted: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    label: str | None = Field(default=None, max_length=120, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_strategy", "strategy_id"),
        Index("ix_orders_account_state", "exchange_account_id", "state"),
        Index(
            "uq_orders_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    exchange_account_id: UUID = Field(
        sa_column=Column(
            "exchange_account_id",
            ForeignKey("trading.exchange_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    symbol: str = Field(max_length=32, nullable=False)
    side: OrderSide = Field(nullable=False)
    type: OrderType = Field(nullable=False)
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    price: Decimal | None = Field(default=None, sa_column=Column(Numeric(18, 8), nullable=True))
    state: OrderState = Field(index=True, nullable=False)
    webhook_payload: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    idempotency_key: str | None = Field(default=None, max_length=200, nullable=True)
    exchange_order_id: str | None = Field(default=None, max_length=120, nullable=True)
    filled_price: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # autoplan Eng E7: CCXT partial fill (filled < quantity) 지원. MDD evaluator가 참조.
    filled_quantity: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    realized_pnl: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # autoplan Eng E2: same-key + different-body 충돌 감지용 payload hash (SHA-256 bytes).
    idempotency_payload_hash: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    error_message: str | None = Field(default=None, max_length=2000, nullable=True)
    # Sprint 7a: Bybit Futures 레버리지/마진 모드. Spot 경로는 NULL.
    leverage: int | None = Field(default=None, nullable=True)
    margin_mode: str | None = Field(default=None, max_length=16, nullable=True)
    submitted_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    # NOTE: terminal timestamp — repository.transition_to_{filled,rejected,cancelled}가
    # 모두 이 컬럼에 기록한다. "filled"라는 이름은 오래된 의미 잔재. 향후 analytics가
    # rejected/cancelled 시점을 따로 쓸 이유가 생기면 terminal_at으로 rename 고려.
    filled_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class KillSwitchEvent(SQLModel, table=True):
    __tablename__ = "kill_switch_events"
    __table_args__ = (
        CheckConstraint(
            "(trigger_type = 'cumulative_loss' AND strategy_id IS NOT NULL AND exchange_account_id IS NULL) "
            "OR (trigger_type IN ('daily_loss','api_error') "
            "    AND exchange_account_id IS NOT NULL AND strategy_id IS NULL)",
            name="ck_kill_switch_events_trigger_scope",
        ),
        Index(
            "ix_kill_switch_events_active_strategy",
            "strategy_id",
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index(
            "ix_kill_switch_events_active_account",
            "exchange_account_id",
            postgresql_where=text("resolved_at IS NULL"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trigger_type: KillSwitchTriggerType = Field(nullable=False)
    strategy_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    exchange_account_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "exchange_account_id",
            ForeignKey("trading.exchange_accounts.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    trigger_value: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    threshold: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    triggered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    resolved_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    resolution_note: str | None = Field(default=None, max_length=500, nullable=True)


class WebhookSecret(SQLModel, table=True):
    __tablename__ = "webhook_secrets"
    __table_args__ = (
        Index("ix_webhook_secrets_strategy_active", "strategy_id", "revoked_at"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    # /cso CSO-1: EncryptionService(MultiFernet)로 암호화 저장. 평문 TEXT 금지.
    # Sprint 6 spec §8 Open Item 1 공식 해소 — DB leak = webhook 위조 방지.
    secret_encrypted: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )

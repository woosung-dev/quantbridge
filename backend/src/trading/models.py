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

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, LargeBinary, SQLModel

from src.common.datetime_types import AwareDateTime


class ExchangeName(StrEnum):
    bybit = "bybit"
    binance = "binance"  # Sprint 7+
    okx = "okx"  # Sprint 7d — CCXT sandbox, spot only, passphrase required


class ExchangeMode(StrEnum):
    demo = "demo"
    live = "live"


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


class LiveSignalInterval(StrEnum):
    """Sprint 26 — Live Signal Auto-Trading 의 평가 주기.

    1m / 5m / 15m / 1h. evaluate_live_signals_task (1분 Beat) 가 list_active_due
    로 interval 별 due 필터링. 5m session 은 5번째 fire 마다 evaluate.
    """

    m1 = "1m"
    m5 = "5m"
    m15 = "15m"
    h1 = "1h"


class LiveSignalEventStatus(StrEnum):
    """Sprint 26 — Transactional outbox event status (codex G.0 P1 #3).

    pending → dispatched (정상 broker 발주) / failed (KillSwitch / NotionalCap / 기타).
    pending 으로 남으면 worker crash recovery 시 재dispatch.
    """

    pending = "pending"
    dispatched = "dispatched"
    failed = "failed"


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
    # Sprint 7d: OKX requires a passphrase on top of key+secret. NULL for exchanges
    # that don't use passphrase (Bybit/Binance).
    passphrase_encrypted: bytes | None = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )
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
    # Sprint 23 BL-102 — dispatch 시점 (exchange, mode, has_leverage) snapshot.
    # _async_execute / _async_fetch_order_status 가 본 snapshot 우선 사용.
    # nullable: legacy row (Sprint 23 이전 생성) 는 NULL → 기존 fallback 동작.
    # schema: {"exchange": "bybit", "mode": "demo", "has_leverage": false}
    # codex G.0 P1 #4: invalid JSON 시 _parse_order_dispatch_snapshot 가 graceful fallback.
    dispatch_snapshot: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
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


class FundingRate(SQLModel, table=True):
    """거래소 funding rate 기록 — 선물 포지션 PnL 보정용.

    8시간마다 정산되는 Bybit/OKX USDT Perpetual funding rate를 저장.
    Alembic: 20260421_0001_add_funding_rates_table.py
    """
    __tablename__ = "funding_rates"
    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "funding_timestamp", name="uq_funding_rates_exchange_symbol_ts"),
        Index("ix_funding_rates_exchange_symbol", "exchange", "symbol"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    symbol: str = Field(max_length=32, nullable=False)
    exchange: ExchangeName = Field(nullable=False)
    funding_rate: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    funding_timestamp: datetime = Field(
        sa_column=Column(AwareDateTime(), nullable=False)
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )


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


# ── Sprint 26: Live Signal Auto-Trading ────────────────────────────────────


class LiveSignalSession(SQLModel, table=True):
    """Sprint 26 — Pine strategy 의 자동 evaluate + broker 발주 session.

    한 사용자 ≤ 5건 active. (user_id, strategy_id, exchange_account_id, symbol)
    partial unique index — `is_active=true` 인 row 만 unique (deactivate 후 재INSERT 가능).

    bar_claim_token: try_claim_bar 의 advisory token (codex G.0 P2 #3).
    last_evaluated_bar_time: CAS 기반 race-safe 평가 (1분 Beat 가 같은 bar 두 번 평가 차단).
    """

    __tablename__ = "live_signal_sessions"
    __table_args__ = (
        Index("ix_live_sessions_user_active", "user_id", "is_active"),
        Index(
            "ix_live_sessions_active_due",
            "is_active",
            "last_evaluated_bar_time",
            postgresql_where=text("is_active = true"),
        ),
        # codex G.0 P2 #2: partial unique index — is_active=true 인 row 만 unique
        Index(
            "uq_live_sessions_active_unique",
            "user_id",
            "strategy_id",
            "exchange_account_id",
            "symbol",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
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
    # Sprint 26 Phase D fix — Alembic 이 String(8) 로 컬럼 생성. SQLAlchemy 가 자동
    # PG enum cast (`$N::livesignalinterval`) 시도해 UndefinedObjectError 발생하므로
    # 명시적 String 컬럼 + Python-level StrEnum 으로 round-trip.
    interval: LiveSignalInterval = Field(sa_column=Column("interval", String(8), nullable=False))
    is_active: bool = Field(default=True)
    last_evaluated_bar_time: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    bar_claim_token: UUID | None = Field(default=None)
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
    deactivated_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )


class LiveSignalState(SQLModel, table=True):
    """Sprint 26 — Live Signal session 의 캐시/UI state.

    Option B (warmup replay) 채택 — 매 evaluate 마다 run_historical 재실행이
    source-of-truth. 이 테이블은 (a) 마지막 strategy_state_report 캐시 (UI 표시용)
    + (b) 누적 통계 (total_closed_trades / total_realized_pnl). 1:1 with session.

    schema_version: 향후 schema migration 안전성 (codex G.0 P3 #2).
    """

    __tablename__ = "live_signal_states"
    __table_args__ = ({"schema": "trading"},)

    session_id: UUID = Field(
        sa_column=Column(
            "session_id",
            ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    schema_version: int = Field(default=1)
    last_strategy_state_report: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    last_open_trades_snapshot: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    total_closed_trades: int = Field(default=0)
    total_realized_pnl: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(18, 8), nullable=False, server_default=text("0")),
    )
    # Sprint 28 Slice 3 (BL-140b) — cumulative realized PnL timeseries.
    # 형식: [{"timestamp_ms": 1700000000000, "cumulative_pnl": "0.123"}, ...]
    # ASC sorted by timestamp_ms. Decimal-first 합산 (Sprint 4 D8) 영구 규칙 적용.
    # nullable=True (legacy row 호환), server_default '[]' (신규 row).
    equity_curve: list[dict[str, object]] | None = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True, server_default=text("'[]'::jsonb")),
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


class LiveSignalEvent(SQLModel, table=True):
    """Sprint 26 — Transactional outbox (codex G.0 P1 #3).

    eval task 가 같은 트랜잭션에서 events INSERT + state upsert + session.last_evaluated
    update + commit. dispatch_live_signal_event_task (별도 task) 가 status=pending event 를
    OrderService.execute. broker 발주 후 mark_dispatched / mark_failed.

    UNIQUE (session_id, bar_time, sequence_no, action, trade_id) — codex G.0 P2 #5
    sequence_no idempotency. 같은 evaluate 가 두 번 fire 해도 INSERT 1번만.

    partial pending index — list_pending 빠른 조회.
    """

    __tablename__ = "live_signal_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "bar_time",
            "sequence_no",
            "action",
            "trade_id",
            name="uq_live_signal_events_idempotency",
        ),
        Index("ix_live_signal_events_session_bar", "session_id", "bar_time"),
        Index(
            "ix_live_signal_events_pending",
            "status",
            postgresql_where=text("status = 'pending'"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(
        sa_column=Column(
            "session_id",
            ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    bar_time: datetime = Field(sa_column=Column(AwareDateTime(), nullable=False))
    sequence_no: int = Field(nullable=False)
    action: str = Field(max_length=16, nullable=False)  # "entry" | "close"
    direction: str = Field(max_length=8, nullable=False)  # "long" | "short"
    trade_id: str = Field(max_length=64, nullable=False)
    qty: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    comment: str = Field(default="", max_length=200)
    # Sprint 26 Phase D fix — interval 과 동일 사유 (PG enum 미생성, String(16) 컬럼).
    status: LiveSignalEventStatus = Field(
        default=LiveSignalEventStatus.pending,
        sa_column=Column("status", String(16), nullable=False, server_default="pending"),
    )
    order_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "order_id",
            ForeignKey("trading.orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    error_message: str | None = Field(default=None, max_length=2000, nullable=True)
    retry_count: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    dispatched_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )

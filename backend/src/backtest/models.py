"""Backtest 도메인 SQLModel 테이블. Sprint 4에서 채움. 변경 시 Alembic 마이그레이션 필수."""
# NOTE: from __future__ import annotations 제거 —
#       SQLAlchemy Relationship forward ref 해석이 PEP 563 lazy eval과 충돌.
#       대신 Relationship에만 문자열 forward ref 사용.

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, LargeBinary, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from src.common.datetime_types import AwareDateTime


class BacktestStatus(StrEnum):
    """Backtest 라이프사이클. CANCELLING은 transient."""

    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"  # transient — Worker 3-guard가 'cancelled'로 최종 전이
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Backtest(SQLModel, table=True):
    __tablename__ = "backtests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    strategy_id: UUID = Field(
        sa_column=Column(
            ForeignKey("strategies.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    # 입력 파라미터 (불변)
    symbol: str = Field(max_length=32, nullable=False)
    timeframe: str = Field(max_length=8, nullable=False)
    period_start: datetime = Field(
        sa_column=Column(AwareDateTime(), nullable=False),
    )
    period_end: datetime = Field(
        sa_column=Column(AwareDateTime(), nullable=False),
    )
    initial_capital: Decimal = Field(max_digits=20, decimal_places=8, nullable=False)

    # 실행 상태
    status: BacktestStatus = Field(
        sa_column=Column(
            SAEnum(BacktestStatus, name="backtest_status"),
            nullable=False,
            default=BacktestStatus.QUEUED,
        )
    )
    celery_task_id: str | None = Field(default=None, max_length=64)

    # 결과 (completed 시에만)
    metrics: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    equity_curve: list[Any] | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = Field(default=None, sa_column=Column(Text))

    # Sprint 31 BL-162a — 사용자 입력 BacktestConfig 5 가정 저장 (TradingView
    # strategy 속성 패턴). nullable — pre-Sprint-31 row 는 NULL → service `_to_detail`
    # 가 engine BacktestConfig default 로 fallback (graceful degrade).
    # schema: {leverage, fees, slippage, include_funding}
    config: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # 멱등성 키 (Sprint 9-6) — 클라이언트가 Idempotency-Key 헤더로 전달
    idempotency_key: str | None = Field(default=None, max_length=128, nullable=True)
    # Sprint 9-6 E2 — same-key + different-body 충돌 감지용 SHA-256 hash (32 bytes).
    # user_id 를 hash payload 에 포함해 cross-user key 재사용도 충돌로 처리.
    # 기존 row (NULL) 는 어떤 body hash 와도 match 되지 않음 (안전성 우선).
    idempotency_payload_hash: bytes | None = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )

    # Sprint 41 Worker H — public read-only share link (revoke 가능).
    # secrets.token_urlsafe(32) → 43-char URL-safe (256-bit entropy). 미생성 = NULL.
    # share_revoked_at IS NULL = active. NOT NULL = revoke (재활성화 불가; 새 share 시 새 토큰).
    # unique + index : 토큰 lookup O(1) + 우연 충돌 차단. 인덱스 이름은 SQLAlchemy
    # 자동 (`ix_backtests_share_token`) — alembic migration 의 명시 이름과 일치.
    share_token: str | None = Field(
        default=None, max_length=64, nullable=True, unique=True, index=True
    )
    share_revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )

    # Relations — Backtest가 BacktestTrade보다 먼저 정의되므로 문자열 forward ref 필수
    trades: list["BacktestTrade"] = Relationship(
        back_populates="backtest",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    __table_args__ = (  # Sprint 3 Strategy 패턴 — 클래스 최하단 배치
        Index("ix_backtests_user_created", "user_id", "created_at"),
        Index("ix_backtests_status", "status"),
        UniqueConstraint("idempotency_key", name="uq_backtests_idempotency_key"),
    )


class BacktestTrade(SQLModel, table=True):
    __tablename__ = "backtest_trades"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    backtest_id: UUID = Field(
        sa_column=Column(
            ForeignKey("backtests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    trade_index: int = Field(nullable=False)

    direction: TradeDirection = Field(
        sa_column=Column(SAEnum(TradeDirection, name="trade_direction"), nullable=False)
    )
    status: TradeStatus = Field(
        sa_column=Column(SAEnum(TradeStatus, name="trade_status"), nullable=False)
    )

    entry_time: datetime = Field(
        sa_column=Column(AwareDateTime(), nullable=False),
    )
    exit_time: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    entry_price: Decimal = Field(max_digits=20, decimal_places=8)
    exit_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    size: Decimal = Field(max_digits=20, decimal_places=8)
    pnl: Decimal = Field(max_digits=20, decimal_places=8)
    return_pct: Decimal = Field(max_digits=12, decimal_places=6)  # 10,000% 여유
    fees: Decimal = Field(max_digits=20, decimal_places=8, default=Decimal("0"))

    backtest: "Backtest" = Relationship(back_populates="trades")

    __table_args__ = (
        Index("ix_backtest_trades_backtest_idx", "backtest_id", "trade_index"),
    )

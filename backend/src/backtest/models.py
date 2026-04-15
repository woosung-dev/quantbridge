"""Backtest 도메인 SQLModel 테이블. Sprint 4에서 채움. 변경 시 Alembic 마이그레이션 필수."""
# NOTE: from __future__ import annotations 제거 —
#       SQLAlchemy Relationship forward ref 해석이 PEP 563 lazy eval과 충돌.
#       대신 Relationship에만 문자열 forward ref 사용.

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    # [임시 workaround — S3-05 follow-up]
    # 정석: 컬럼을 DateTime(timezone=True) (TIMESTAMPTZ)로 정의 + datetime.now(UTC) (tz-aware) 반환.
    # 현재: migration이 sa.DateTime() (naive)으로 생성됐고 asyncpg가 tz-aware를 거부 → naive UTC 반환.
    # TimescaleDB hypertable 도입 시점(Sprint 5+) 전에 docs/TODO.md S3-05로 복구 예정.
    return datetime.now(UTC).replace(tzinfo=None)


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
    period_start: datetime = Field(nullable=False)
    period_end: datetime = Field(nullable=False)
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

    # Timestamps (S3-05 workaround — naive UTC)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Relations — Backtest가 BacktestTrade보다 먼저 정의되므로 문자열 forward ref 필수
    trades: list["BacktestTrade"] = Relationship(
        back_populates="backtest",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    __table_args__ = (  # Sprint 3 Strategy 패턴 — 클래스 최하단 배치
        Index("ix_backtests_user_created", "user_id", "created_at"),
        Index("ix_backtests_status", "status"),
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

    entry_time: datetime = Field(nullable=False)
    exit_time: datetime | None = Field(default=None)
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

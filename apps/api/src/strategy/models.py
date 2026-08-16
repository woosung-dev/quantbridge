"""strategy 도메인 SQLModel 테이블. Sprint 3에서 Strategy 추가."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, SQLModel

from src.common.datetime_types import AwareDateTime

PINE_V2_PARSER_VERSION = "pine_v2"


class ParseStatus(StrEnum):
    ok = "ok"
    unsupported = "unsupported"
    error = "error"


class PineVersion(StrEnum):
    v4 = "v4"
    v5 = "v5"


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"
    __table_args__ = (
        Index(
            "ix_strategies_owner_active_updated",
            "user_id",
            "is_archived",
            "updated_at",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("users.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    name: str = Field(max_length=120, nullable=False)
    description: str | None = Field(default=None, max_length=2000, nullable=True)
    pine_source: str = Field(nullable=False)
    # 최신 불변 source snapshot. Strategy 생성 시에는 FK 순환을 피하려고 잠시 NULL 이고,
    # StrategyService 가 같은 트랜잭션 안에서 StrategyVersion 생성 뒤 항상 채운다.
    strategy_version_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey(
                "strategy_versions.id",
                name="fk_strategies_strategy_version_id_strategy_versions",
                ondelete="RESTRICT",
                use_alter=True,
            ),
            nullable=True,
            index=True,
        ),
    )
    pine_version: PineVersion = Field(nullable=False)
    parse_status: ParseStatus = Field(index=True, nullable=False)
    parse_errors: list[dict[str, object]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    timeframe: str | None = Field(default=None, max_length=16, nullable=True)
    symbol: str | None = Field(default=None, max_length=32, nullable=True)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # Sprint 7d: market session gate. Empty list = 24h (no filter). Values are a
    # subset of {"asia", "london", "ny"} enforced at the Pydantic schema layer.
    # Nullable in DB for backward compatibility with pre-migration rows.
    trading_sessions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True, server_default="[]"),
    )
    # Sprint 26: Live Signal Auto-Trading 의 trading params (leverage / margin_mode /
    # position_size_pct). StrategySettings Pydantic schema 가 read path 에서 validate.
    # None = unset (Live Signal 시작 차단), dict = StrategySettings 통과 시만 active 허용.
    # schema_version 컬럼 P3 #2 — 향후 schema migration 안전성.
    settings: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    is_archived: bool = Field(default=False, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
        ),
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


class StrategyVersion(SQLModel, table=True):
    """실행 입력으로 쓰는 불변 Pine source snapshot."""

    __tablename__ = "strategy_versions"
    __table_args__ = (Index("ix_strategy_versions_strategy_created", "strategy_id", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(
        sa_column=Column(
            ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    pine_source: str = Field(sa_column=Column(Text, nullable=False))
    source_hash: str = Field(sa_column=Column(String(64), nullable=False))
    parser_version: str = Field(
        default=PINE_V2_PARSER_VERSION,
        sa_column=Column(String(32), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )

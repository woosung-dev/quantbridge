"""Python 연구 전략의 소유권·불변 버전·비동기 실행 원장."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC)


class PythonStrategy(SQLModel, table=True):
    __tablename__ = "python_strategies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    name: str = Field(max_length=120)
    version_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey(
                "python_strategy_versions.id",
                name="fk_python_strategy_current_version",
                use_alter=True,
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class PythonStrategyVersion(SQLModel, table=True):
    __tablename__ = "python_strategy_versions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(foreign_key="python_strategies.id", ondelete="CASCADE", index=True)
    source: str = Field(sa_column=Column(Text, nullable=False))
    source_hash: str = Field(max_length=64)
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    warmup_bars: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class PythonBacktest(SQLModel, table=True):
    __tablename__ = "python_backtests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','completed','failed','cancelled')",
            name="ck_python_backtest_status",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    strategy_id: UUID = Field(foreign_key="python_strategies.id", ondelete="CASCADE", index=True)
    version_id: UUID = Field(foreign_key="python_strategy_versions.id", ondelete="CASCADE")
    status: str = Field(default="pending", sa_column=Column(String(16), nullable=False))
    request: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))

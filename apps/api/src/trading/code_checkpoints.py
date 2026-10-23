"""코드 실행기의 재시작 입력. 현재 포지션을 과거 봉에 덮어쓰지 않는다."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class LiveCodeBar(SQLModel, table=True):
    __tablename__ = "live_code_bars"
    __table_args__ = (
        UniqueConstraint("session_id", "bar_time", name="uq_live_code_bars_session_time"),
        UniqueConstraint("session_id", "sequence", name="uq_live_code_bars_session_sequence"),
        CheckConstraint(
            "status IN ('warmup','prepared','delivered','blocked')", name="ck_live_code_bars_status"
        ),
        {"schema": "trading"},
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("trading.live_signal_sessions.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    bar_time: datetime = Field(sa_column=Column(AwareDateTime(), nullable=False))
    sequence: int = Field(nullable=False)
    execution_hash: str = Field(max_length=64, nullable=False)
    input_hash: str = Field(max_length=64, nullable=False)
    bar: dict[str, object] = Field(sa_column=Column(JSONB, nullable=False))
    position: dict[str, object] = Field(sa_column=Column(JSONB, nullable=False))
    delivery_args: dict[str, object] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    intent: str = Field(sa_column=Column(String(8), nullable=False))
    status: str = Field(max_length=16, nullable=False)
    is_warmup: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )

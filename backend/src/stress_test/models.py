"""stress_test 도메인 SQLModel 테이블.

Sprint H2 Phase B — Monte Carlo + Walk-Forward 결과 영속화.
변경 시 Alembic 마이그레이션 필수.

NOTE: from __future__ import annotations 제거 —
      SQLAlchemy Relationship forward ref 해석이 PEP 563 lazy eval 과 충돌.
      backtest/models.py 와 동일 패턴.
"""
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class StressTestKind(StrEnum):
    """Stress test 종류 — Monte Carlo / Walk-Forward / Cost Assumption / Param Stability.

    Sprint 50: COST_ASSUMPTION_SENSITIVITY (BacktestConfig fees x slippage 9-cell grid).
    Sprint 51 BL-220: PARAM_STABILITY (pine_v2 input override 9-cell grid sweep —
    EMA period x stop loss % 등 strategy parameter sweep).

    LESSON-066 의무: SAEnum + StrEnum 조합에서 SAEnum 은 member NAME (uppercase) 을
    DB enum value 로 사용. alembic migration 의 enum value 도 uppercase 일관성 유지
    (Sprint 50 BL-221 P0 hotfix `da7e52e` 참조).
    """

    MONTE_CARLO = "monte_carlo"
    WALK_FORWARD = "walk_forward"
    COST_ASSUMPTION_SENSITIVITY = "cost_assumption_sensitivity"
    PARAM_STABILITY = "param_stability"


class StressTestStatus(StrEnum):
    """Stress test 실행 라이프사이클."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StressTest(SQLModel, table=True):
    __tablename__ = "stress_tests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # 원본 백테스트 — delete 시 stress test 영속 유지 위해 RESTRICT.
    backtest_id: UUID = Field(
        sa_column=Column(
            ForeignKey("backtests.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    kind: StressTestKind = Field(
        sa_column=Column(
            SAEnum(StressTestKind, name="stress_test_kind"),
            nullable=False,
        )
    )
    status: StressTestStatus = Field(
        sa_column=Column(
            SAEnum(StressTestStatus, name="stress_test_status"),
            nullable=False,
            default=StressTestStatus.QUEUED,
        )
    )

    # 입력 파라미터 (JSONB) — MC: {n_samples, seed}; WFA: {train_bars, test_bars, step_bars, max_folds}.
    params: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )

    # 결과 — completed 시에만. kind 별 스키마 상이.
    # MC: {samples, ci_lower_95, ci_upper_95, median_final_equity, max_drawdown_mean,
    #      max_drawdown_p95, equity_percentiles: {"5": [...], ...}}.
    # WFA: {folds: [...], aggregate_oos_return, degradation_ratio,
    #       valid_positive_regime, total_possible_folds, was_truncated}.
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = Field(default=None, sa_column=Column(Text))

    celery_task_id: str | None = Field(default=None, max_length=64)

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

    __table_args__ = (
        Index("ix_stress_tests_user_created", "user_id", "created_at"),
        Index("ix_stress_tests_status", "status"),
    )

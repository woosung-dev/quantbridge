"""Optimizer 도메인 SQLModel 테이블 — Sprint 53 skeleton (Sprint 54 본격 구현 prereq).

DB migration 의무 보류 (codex G.0 P1#8): param_space grammar 확정 전 alembic 생성 X.
Sprint 54 Grid Search service 와 동시에 table + enum 생성. entity 정의만 lock.

NOTE: from __future__ import annotations 제거 — SQLAlchemy Relationship forward ref
      해석이 PEP 563 lazy eval 과 충돌. stress_test/models.py 와 동일 패턴.

LESSON-066 의무: SAEnum + StrEnum 조합 = DB enum value 는 member NAME (uppercase) 저장.
                 alembic migration 의 enum value 도 uppercase 일관성 (Sprint 50 BL-221 P0
                 hotfix `da7e52e` 영구 검증 path).

SAEnum `values_callable` 옵션 금지 (codex G.0 P1#5): 옵션 사용 시 lowercase 저장
경로로 회귀 → BL-221 재발.
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


class OptimizationKind(StrEnum):
    """Optimizer 알고리즘 종류 — Sprint 56 = Grid Search + Bayesian + Genetic.

    Sprint 56 BL-233 (Genetic executor 본격) 따라 GENETIC 활성. LESSON-066 7차 path =
    SAEnum + StrEnum member name (uppercase) 일관성 유지. alembic 마이그레이션 안
    `ALTER TYPE ... ADD VALUE 'GENETIC'` (uppercase) 동시 진행 의무.
    """

    GRID_SEARCH = "grid_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"


class OptimizationStatus(StrEnum):
    """Optimizer 실행 라이프사이클 — StressTestStatus grammar 재사용."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OptimizationRun(SQLModel, table=True):
    """Optimizer 실행 단일 row. Sprint 54 본격 service + Celery task 추가 시 라이프사이클 풀."""

    __tablename__ = "optimization_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    # 원본 백테스트 — delete 시 optimization 결과 영속 위해 RESTRICT (StressTest 패턴 mirror).
    backtest_id: UUID = Field(
        sa_column=Column(
            ForeignKey("backtests.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    kind: OptimizationKind = Field(
        sa_column=Column(
            # SAEnum: values_callable 옵션 금지 (codex P1#5, BL-221 재발 함정).
            # 기본 동작 = StrEnum member NAME (uppercase) 저장.
            SAEnum(OptimizationKind, name="optimization_kind"),
            nullable=False,
        )
    )
    status: OptimizationStatus = Field(
        sa_column=Column(
            SAEnum(OptimizationStatus, name="optimization_status"),
            nullable=False,
            default=OptimizationStatus.QUEUED,
        ),
        default=OptimizationStatus.QUEUED,
    )

    # 탐색 공간 grammar (discriminated union — IntegerField / DecimalField / CategoricalField).
    # schemas.ParamSpace 의 model_dump() 결과를 직렬화.
    param_space: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )

    # 결과 (Sprint 54 본격 구현 시 채움) — kind 별 schema 상이.
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    error_message: str | None = Field(default=None, sa_column=Column(Text))

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
        # codex P2 권고 — list/poll 효율 위해 composite + status index 의무.
        Index("ix_optimization_runs_user_created", "user_id", "created_at"),
        Index("ix_optimization_runs_status", "status"),
    )

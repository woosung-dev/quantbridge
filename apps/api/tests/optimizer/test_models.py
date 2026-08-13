# OptimizationRun entity 정의 검증 (Sprint 53 BL-228 skeleton, DB migration 보류).

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Enum as SAEnum

from src.optimizer.models import (
    OptimizationKind,
    OptimizationRun,
    OptimizationStatus,
)


def test_optimization_run_default_status_queued() -> None:
    """default status = QUEUED (stress_test grammar 재사용)."""
    run = OptimizationRun(
        user_id=uuid4(),
        backtest_id=uuid4(),
        kind=OptimizationKind.GRID_SEARCH,
        param_space={"schema_version": 1, "parameters": {}},
        created_at=datetime.now(UTC),
    )
    assert run.status == OptimizationStatus.QUEUED


def test_optimization_run_kind_enum_uppercase_db_value() -> None:
    """SAEnum + StrEnum = DB enum value 는 uppercase member name (LESSON-066).

    Sprint 50 BL-221 P0 hotfix 영구 검증 path. SAEnum.name == "optimization_kind".
    """
    # SAEnum column 의 enum type name = postgres enum 타입 식별자
    kind_column = OptimizationRun.__table__.c.kind
    sa_enum = kind_column.type
    assert isinstance(sa_enum, SAEnum)
    assert sa_enum.name == "optimization_kind"

    # SAEnum 의 enum class = StrEnum
    assert sa_enum.enum_class is OptimizationKind

    # member name = uppercase (postgres enum value 로 저장됨)
    member_names = [m.name for m in OptimizationKind]
    assert "GRID_SEARCH" in member_names
    assert "BAYESIAN" in member_names
    # Sprint 56 BL-233 — Genetic 추가 (LESSON-066 7차 검증).
    assert "GENETIC" in member_names


def test_optimization_run_status_enum_name() -> None:
    """status SAEnum name = optimization_status (stress_test_status grammar mirror)."""
    status_column = OptimizationRun.__table__.c.status
    sa_enum = status_column.type
    assert isinstance(sa_enum, SAEnum)
    assert sa_enum.name == "optimization_status"
    assert sa_enum.enum_class is OptimizationStatus


def test_optimization_run_fk_user_cascade_backtest_restrict() -> None:
    """FK 정책 — user_id CASCADE, backtest_id RESTRICT (stress_test 패턴 mirror)."""
    user_fk = next(iter(OptimizationRun.__table__.c.user_id.foreign_keys))
    backtest_fk = next(iter(OptimizationRun.__table__.c.backtest_id.foreign_keys))

    assert user_fk.column.table.name == "users"
    assert user_fk.ondelete == "CASCADE"

    assert backtest_fk.column.table.name == "backtests"
    assert backtest_fk.ondelete == "RESTRICT"


def test_optimization_run_table_indexes_match_spec() -> None:
    """codex P2 권고 — user_id+created_at / status / backtest_id index 의무."""
    indexes = {idx.name for idx in OptimizationRun.__table__.indexes}
    # backtest_id / user_id 은 Column(index=True) 가 자동 생성 (ix_<table>_<col>)
    # user_id+created_at composite 는 __table_args__ Index() 으로 명시
    assert "ix_optimization_runs_user_created" in indexes
    assert "ix_optimization_runs_status" in indexes

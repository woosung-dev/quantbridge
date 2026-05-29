# CF3 — Optimizer stale-RUNNING reclaim 회귀 (crash 한 RUNNING run 이 영구 stuck 되지 않도록)
"""Phase C-1 CF3: optimizer 도메인 stale-RUNNING reclaim.

backtest 의 reclaim_stale 패턴을 mirror. optimizer worker 가 RUNNING 중 crash 하면
status 가 영구 RUNNING 으로 남아 UI 에 hung run 으로 노출된다. threshold 초과
RUNNING → FAILED 로 전이한다. (optimizer 는 cancel 기능이 없어 CANCELLING 상태 없음.)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.optimizer.models import OptimizationKind, OptimizationRun, OptimizationStatus
from src.optimizer.repository import OptimizationRepository
from tests.stress_test.helpers import seed_user_strategy_backtest


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _seed_run(
    db: AsyncSession,
    user_id,
    backtest_id,
    *,
    status: OptimizationStatus,
    started_at: datetime | None,
) -> OptimizationRun:
    run = OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=OptimizationKind.GRID_SEARCH,
        status=status,
        param_space={"schema_version": 1, "parameters": {}},
        started_at=started_at,
    )
    db.add(run)
    await db.flush()
    return run


@pytest.mark.asyncio
async def test_reclaim_stale_running_marks_failed(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    run = await _seed_run(
        db_session,
        user.id,
        backtest.id,
        status=OptimizationStatus.RUNNING,
        started_at=_utcnow() - timedelta(hours=2),
    )

    repo = OptimizationRepository(db_session)
    reclaimed = await repo.reclaim_stale(threshold_seconds=1800, now=_utcnow())

    assert reclaimed == 1
    await db_session.refresh(run)
    assert run.status == OptimizationStatus.FAILED
    assert run.completed_at is not None
    assert run.error_message is not None


@pytest.mark.asyncio
async def test_reclaim_stale_leaves_fresh_running_and_queued(
    db_session: AsyncSession,
) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    fresh = await _seed_run(
        db_session, user.id, backtest.id, status=OptimizationStatus.RUNNING, started_at=_utcnow()
    )
    queued = await _seed_run(
        db_session, user.id, backtest.id, status=OptimizationStatus.QUEUED, started_at=None
    )

    repo = OptimizationRepository(db_session)
    reclaimed = await repo.reclaim_stale(threshold_seconds=1800, now=_utcnow())

    assert reclaimed == 0
    await db_session.refresh(fresh)
    await db_session.refresh(queued)
    assert fresh.status == OptimizationStatus.RUNNING
    assert queued.status == OptimizationStatus.QUEUED

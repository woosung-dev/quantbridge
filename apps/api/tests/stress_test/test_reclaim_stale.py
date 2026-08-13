# CF3 — Stress Test stale-RUNNING reclaim 회귀 (crash 한 RUNNING run 이 영구 stuck 되지 않도록)
"""Phase C-1 CF3: stress_test 도메인 stale-RUNNING reclaim.

backtest 의 reclaim_stale 패턴 mirror. stress_test worker 가 RUNNING 중 crash 하면
status 가 영구 RUNNING 으로 남는다. threshold 초과 RUNNING → FAILED 전이.
(stress_test 는 cancel 기능이 없어 CANCELLING 상태 없음.)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.repository import StressTestRepository
from tests.stress_test.helpers import seed_user_strategy_backtest


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _seed_run(
    db: AsyncSession,
    user_id,
    backtest_id,
    *,
    status: StressTestStatus,
    started_at: datetime | None,
) -> StressTest:
    st = StressTest(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=StressTestKind.MONTE_CARLO,
        status=status,
        params={"n_samples": 50, "seed": 42},
        started_at=started_at,
    )
    db.add(st)
    await db.flush()
    return st


@pytest.mark.asyncio
async def test_reclaim_stale_running_marks_failed(db_session: AsyncSession) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    st = await _seed_run(
        db_session,
        user.id,
        backtest.id,
        status=StressTestStatus.RUNNING,
        started_at=_utcnow() - timedelta(hours=2),
    )

    repo = StressTestRepository(db_session)
    reclaimed = await repo.reclaim_stale(threshold_seconds=1800, now=_utcnow())

    assert reclaimed == 1
    await db_session.refresh(st)
    assert st.status == StressTestStatus.FAILED
    assert st.completed_at is not None
    assert st.error is not None


@pytest.mark.asyncio
async def test_reclaim_stale_leaves_fresh_running_and_queued(
    db_session: AsyncSession,
) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    fresh = await _seed_run(
        db_session, user.id, backtest.id, status=StressTestStatus.RUNNING, started_at=_utcnow()
    )
    queued = await _seed_run(
        db_session, user.id, backtest.id, status=StressTestStatus.QUEUED, started_at=None
    )

    repo = StressTestRepository(db_session)
    reclaimed = await repo.reclaim_stale(threshold_seconds=1800, now=_utcnow())

    assert reclaimed == 0
    await db_session.refresh(fresh)
    await db_session.refresh(queued)
    assert fresh.status == StressTestStatus.RUNNING
    assert queued.status == StressTestStatus.QUEUED

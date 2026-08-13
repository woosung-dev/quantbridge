"""Worker execution 실패 → status=failed + error 메시지 기록."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.stress_test.models import (
    StressTest,
    StressTestKind,
    StressTestStatus,
)
from src.stress_test.repository import StressTestRepository
from tests.stress_test.helpers import make_service, seed_user_strategy_backtest


@pytest.mark.asyncio
async def test_mc_worker_fails_when_equity_curve_absent(
    db_session: AsyncSession,
) -> None:
    """equity_curve 가 None 이면 MC 불가 → status=failed."""
    user, _, backtest = await seed_user_strategy_backtest(
        db_session, include_equity_curve=False
    )
    # explicit None 강제
    backtest.equity_curve = None
    await db_session.flush()

    st = StressTest(
        id=uuid4(),
        user_id=user.id,
        backtest_id=backtest.id,
        kind=StressTestKind.MONTE_CARLO,
        status=StressTestStatus.QUEUED,
        params={"n_samples": 50, "seed": 42},
    )
    db_session.add(st)
    await db_session.flush()

    service, _ = make_service(db_session)
    await service.run(st.id)

    repo = StressTestRepository(db_session)
    reloaded = await repo.get_by_id(st.id)
    assert reloaded is not None
    assert reloaded.status == StressTestStatus.FAILED
    assert reloaded.error is not None
    assert "equity_curve" in reloaded.error.lower() or "short" in reloaded.error.lower()

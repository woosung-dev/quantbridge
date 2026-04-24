"""StressTestService.run (MC) happy path — equity_curve JSONB → MC result JSONB 저장."""

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
async def test_monte_carlo_worker_produces_result_jsonb(
    db_session: AsyncSession,
) -> None:
    user, _, backtest = await seed_user_strategy_backtest(db_session)
    assert backtest.equity_curve  # sanity — helper 가 채움

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

    # reload from DB
    repo = StressTestRepository(db_session)
    reloaded = await repo.get_by_id(st.id)
    assert reloaded is not None
    assert reloaded.status == StressTestStatus.COMPLETED, reloaded.error
    assert reloaded.result is not None
    # MC JSONB 필드 확인
    assert "ci_lower_95" in reloaded.result
    assert "ci_upper_95" in reloaded.result
    assert "equity_percentiles" in reloaded.result
    # percentiles keys 는 string ("5", "25", ...)
    pctls = reloaded.result["equity_percentiles"]
    assert set(pctls.keys()) == {"5", "25", "50", "75", "95"}
    # 각 series 는 string list
    for k, series in pctls.items():
        assert all(isinstance(v, str) for v in series), k

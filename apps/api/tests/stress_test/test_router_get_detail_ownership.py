"""GET /stress-tests/{id} — 다른 user 소유 stress_test → 404."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.stress_test.dependencies import get_stress_test_service
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from tests.stress_test.helpers import make_service, seed_user_strategy_backtest


@pytest.mark.asyncio
async def test_cannot_access_other_users_stress_test(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    # 다른 user 소유의 backtest + stress_test 생성 (seed_user 가 다른 user 생성).
    other_user, _, backtest = await seed_user_strategy_backtest(db_session)

    other_st = StressTest(
        id=uuid4(),
        user_id=other_user.id,
        backtest_id=backtest.id,
        kind=StressTestKind.MONTE_CARLO,
        status=StressTestStatus.COMPLETED,
        params={"n_samples": 100, "seed": 42},
    )
    db_session.add(other_st)
    await db_session.flush()

    service, _ = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service

    try:
        resp = await client.get(f"/api/v1/stress-tests/{other_st.id}")
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "stress_test_not_found"

"""POST /stress-tests/walk-forward — 202 + dispatcher 호출 확인."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.stress_test.dependencies import get_stress_test_service
from src.stress_test.models import StressTestKind, StressTestStatus
from tests.stress_test.helpers import make_service, seed_user_strategy_backtest


@pytest.mark.asyncio
async def test_walk_forward_submit_returns_202(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    _, _, backtest = await seed_user_strategy_backtest(db_session)
    backtest.user_id = mock_clerk_auth.id
    await db_session.flush()

    service, dispatcher = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service

    try:
        resp = await client.post(
            "/api/v1/stress-tests/walk-forward",
            json={
                "backtest_id": str(backtest.id),
                "params": {
                    "train_bars": 50,
                    "test_bars": 10,
                    "max_folds": 5,
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["kind"] == StressTestKind.WALK_FORWARD.value
    assert data["status"] == StressTestStatus.QUEUED.value
    assert len(dispatcher.dispatched) == 1

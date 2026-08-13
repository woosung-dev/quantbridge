"""POST /stress-tests/monte-carlo — 202 + dispatcher 호출 확인."""

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
async def test_monte_carlo_submit_returns_202_with_stress_test_id(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    # bootstrap backtest — authed_user owns it.
    _, _, backtest = await seed_user_strategy_backtest(db_session)
    # 소유자 일치 필요 — mock_clerk_auth 가 authed_user 이므로 이전 user 재사용 안 됨.
    # authed_user 와 동일 소유자로 재시드.
    backtest.user_id = mock_clerk_auth.id
    await db_session.flush()

    service, dispatcher = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service

    try:
        resp = await client.post(
            "/api/v1/stress-tests/monte-carlo",
            json={
                "backtest_id": str(backtest.id),
                "params": {"n_samples": 100, "seed": 42},
            },
        )
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["kind"] == StressTestKind.MONTE_CARLO.value
    assert data["status"] == StressTestStatus.QUEUED.value
    assert "stress_test_id" in data
    # Dispatcher 가 정확히 1회 호출됐고 task_id 가 기록되었는지 확인
    assert len(dispatcher.dispatched) == 1


@pytest.mark.asyncio
async def test_monte_carlo_submit_fails_if_backtest_not_completed(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    from src.backtest.models import BacktestStatus

    _, _, backtest = await seed_user_strategy_backtest(
        db_session, backtest_status=BacktestStatus.QUEUED
    )
    backtest.user_id = mock_clerk_auth.id
    await db_session.flush()

    service, dispatcher = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service

    try:
        resp = await client.post(
            "/api/v1/stress-tests/monte-carlo",
            json={"backtest_id": str(backtest.id)},
        )
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["detail"]["code"] == "backtest_not_completed"
    assert len(dispatcher.dispatched) == 0

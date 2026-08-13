# POST /stress-tests/param-stability — 202 + dispatcher 호출 + LESSON-066 풀 chain 검증 (Sprint 51 BL-220 Slice 6)
"""Sprint 51 Slice 6 — Param Stability router e2e (Sprint 50 cost-assumption 1:1 패턴 재사용).

LESSON-066 2차 검증 path:
- POST /stress-tests/param-stability → 202 + service.submit_param_stability called
- DB INSERT (kind='PARAM_STABILITY' enum value uppercase/lowercase 일관성)
- backtest not completed → 409 reject (CurrentUser auth path 정합)
- dispatcher.dispatch_stress_test 정확히 1회 호출
"""

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
async def test_param_stability_submit_returns_202_with_stress_test_id(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    """LESSON-066 풀 chain — router → service → repo INSERT → DB round-trip."""
    _, _, backtest = await seed_user_strategy_backtest(db_session)
    backtest.user_id = mock_clerk_auth.id
    await db_session.flush()

    service, dispatcher = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service

    try:
        resp = await client.post(
            "/api/v1/stress-tests/param-stability",
            json={
                "backtest_id": str(backtest.id),
                "params": {
                    "param_grid": {
                        "emaPeriod": ["10", "20", "30"],
                        "stopLossPct": ["1.0", "2.0", "3.0"],
                    },
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["kind"] == StressTestKind.PARAM_STABILITY.value
    assert data["status"] == StressTestStatus.QUEUED.value
    assert "stress_test_id" in data
    # dispatcher 정확 1회 호출 (LESSON-019 spy + LESSON-066 path 합산)
    assert len(dispatcher.dispatched) == 1


@pytest.mark.asyncio
async def test_param_stability_submit_fails_if_backtest_not_completed(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    """backtest 미완료 → 409 reject (CurrentUser auth + ensure_completed gate 정합)."""
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
            "/api/v1/stress-tests/param-stability",
            json={
                "backtest_id": str(backtest.id),
                "params": {
                    "param_grid": {
                        "emaPeriod": ["10", "20", "30"],
                        "stopLossPct": ["1.0", "2.0", "3.0"],
                    },
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["detail"]["code"] == "backtest_not_completed"
    assert len(dispatcher.dispatched) == 0


@pytest.mark.asyncio
async def test_param_stability_submit_rejects_grid_exceeding_9_cells(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    """10+ cell grid → 422 reject (Sprint 50 codex P1#5 동일 강제)."""
    _, _, backtest = await seed_user_strategy_backtest(db_session)
    backtest.user_id = mock_clerk_auth.id
    await db_session.flush()

    service, dispatcher = make_service(db_session)
    app.dependency_overrides[get_stress_test_service] = lambda: service

    try:
        # 4×3 = 12 cell → 9 cap 초과
        resp = await client.post(
            "/api/v1/stress-tests/param-stability",
            json={
                "backtest_id": str(backtest.id),
                "params": {
                    "param_grid": {
                        "emaPeriod": ["10", "20", "30", "40"],
                        "stopLossPct": ["1.0", "2.0", "3.0"],
                    },
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_stress_test_service, None)

    assert resp.status_code == 422, resp.text
    assert len(dispatcher.dispatched) == 0

"""Stress Test REST API.

POST /stress-tests/monte-carlo        — submit MC (202)
POST /stress-tests/walk-forward       — submit WFA (202)
GET  /stress-tests                    — list (page)
GET  /stress-tests/{id}               — detail
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.pagination import Page
from src.stress_test.dependencies import get_stress_test_service
from src.stress_test.schemas import (
    MonteCarloSubmitRequest,
    StressTestCreatedResponse,
    StressTestDetail,
    StressTestSummary,
    WalkForwardSubmitRequest,
)
from src.stress_test.service import StressTestService

router = APIRouter(prefix="/stress-tests", tags=["stress_test"])


@router.post(
    "/monte-carlo",
    response_model=StressTestCreatedResponse,
    status_code=202,
)
async def submit_monte_carlo(
    data: MonteCarloSubmitRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_monte_carlo(data, user_id=user.id)


@router.post(
    "/walk-forward",
    response_model=StressTestCreatedResponse,
    status_code=202,
)
async def submit_walk_forward(
    data: WalkForwardSubmitRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_walk_forward(data, user_id=user.id)


@router.get("", response_model=Page[StressTestSummary])
async def list_stress_tests(
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    backtest_id: UUID | None = Query(None),
) -> Page[StressTestSummary]:
    return await service.list(
        user_id=user.id, limit=limit, offset=offset, backtest_id=backtest_id
    )


@router.get("/{stress_test_id}", response_model=StressTestDetail)
async def get_stress_test(
    stress_test_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestDetail:
    return await service.get(stress_test_id, user_id=user.id)

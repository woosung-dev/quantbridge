"""Stress Test REST API.

POST /stress-tests/monte-carlo                — submit MC (202)
POST /stress-tests/walk-forward               — submit WFA (202)
POST /stress-tests/cost-assumption-sensitivity — submit CA (202, Sprint 50)
GET  /stress-tests                            — list (page)
GET  /stress-tests/{id}                       — detail
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.pagination import Page
from src.common.rate_limit import limiter
from src.stress_test.dependencies import get_stress_test_service
from src.stress_test.schemas import (
    CostAssumptionSubmitRequest,
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
@limiter.limit("5/minute")
async def submit_monte_carlo(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: MonteCarloSubmitRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_monte_carlo(data, user_id=user.id)


@router.post(
    "/walk-forward",
    response_model=StressTestCreatedResponse,
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_walk_forward(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: WalkForwardSubmitRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_walk_forward(data, user_id=user.id)


@router.post(
    "/cost-assumption-sensitivity",
    response_model=StressTestCreatedResponse,
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_cost_assumption_sensitivity(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: CostAssumptionSubmitRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    """Sprint 50 — Cost Assumption Sensitivity (fees x slippage 9-cell grid)."""
    return await service.submit_cost_assumption_sensitivity(
        data, user_id=user.id
    )


@router.get("", response_model=Page[StressTestSummary])
async def list_stress_tests(
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    backtest_id: UUID | None = Query(None),
) -> Page[StressTestSummary]:
    return await service.list(user_id=user.id, limit=limit, offset=offset, backtest_id=backtest_id)


@router.get("/{stress_test_id}", response_model=StressTestDetail)
async def get_stress_test(
    stress_test_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestDetail:
    return await service.get(stress_test_id, user_id=user.id)

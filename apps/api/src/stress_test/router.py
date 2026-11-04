"""Stress Test REST API 라우터.

POST /stress-tests/monte-carlo                — MC 제출 (202)
POST /stress-tests/walk-forward               — WFA 제출 (202)
POST /stress-tests/cost-assumption-sensitivity — CA 제출 (202, Sprint 50)
POST /stress-tests/param-stability            — PS 제출 (202, Sprint 51 BL-220)
GET  /stress-tests                            — 목록 조회 (page)
GET  /stress-tests/{id}                       — 상세 조회
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from src.auth.dependencies import CurrentUserDep
from src.common.pagination import Page
from src.common.rate_limit import limiter
from src.stress_test.dependencies import StressTestServiceDep
from src.stress_test.schemas import (
    CostAssumptionSubmitRequest,
    MonteCarloSubmitRequest,
    ParamStabilitySubmitRequest,
    StressTestCreatedResponse,
    StressTestDetail,
    StressTestSummary,
    WalkForwardSubmitRequest,
)

router = APIRouter(prefix="/stress-tests", tags=["stress_test"])


@router.post(
    "/monte-carlo",
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_monte_carlo(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: MonteCarloSubmitRequest,
    response: Response,
    user: CurrentUserDep,
    service: StressTestServiceDep,
) -> StressTestCreatedResponse:
    return await service.submit_monte_carlo(data, user_id=user.id)


@router.post(
    "/walk-forward",
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_walk_forward(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: WalkForwardSubmitRequest,
    response: Response,
    user: CurrentUserDep,
    service: StressTestServiceDep,
) -> StressTestCreatedResponse:
    return await service.submit_walk_forward(data, user_id=user.id)


@router.post(
    "/cost-assumption-sensitivity",
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_cost_assumption_sensitivity(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: CostAssumptionSubmitRequest,
    response: Response,
    user: CurrentUserDep,
    service: StressTestServiceDep,
) -> StressTestCreatedResponse:
    """Sprint 50 — Cost Assumption Sensitivity (fees x slippage 9-cell grid)."""
    return await service.submit_cost_assumption_sensitivity(data, user_id=user.id)


@router.post(
    "/param-stability",
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_param_stability(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: ParamStabilitySubmitRequest,
    response: Response,
    user: CurrentUserDep,
    service: StressTestServiceDep,
) -> StressTestCreatedResponse:
    """Sprint 51 BL-220 — Param Stability (pine_v2 input override 9-cell grid)."""
    return await service.submit_param_stability(data, user_id=user.id)


@router.get("")
async def list_stress_tests(
    user: CurrentUserDep,
    service: StressTestServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    backtest_id: Annotated[UUID | None, Query()] = None,
) -> Page[StressTestSummary]:
    return await service.list(user_id=user.id, limit=limit, offset=offset, backtest_id=backtest_id)


@router.get("/{stress_test_id}")
async def get_stress_test(
    stress_test_id: UUID,
    user: CurrentUserDep,
    service: StressTestServiceDep,
) -> StressTestDetail:
    return await service.get(stress_test_id, user_id=user.id)

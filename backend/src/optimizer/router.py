"""optimizer HTTP 라우터 — Sprint 54 Phase 3 Grid Search MVP.

POST /optimizer/runs/grid-search — submit Grid Search (202)
GET  /optimizer/runs              — list (page)
GET  /optimizer/runs/{id}         — detail
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.pagination import Page
from src.common.rate_limit import limiter
from src.optimizer.dependencies import get_optimizer_service
from src.optimizer.schemas import (
    CreateOptimizationRunRequest,
    OptimizationRunResponse,
)
from src.optimizer.service import OptimizerService

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


@router.post(
    "/runs/grid-search",
    response_model=OptimizationRunResponse,
    status_code=202,
)
@limiter.limit("5/minute")
async def submit_grid_search(
    request: Request,  # slowapi key 추출에 사용
    data: CreateOptimizationRunRequest,
    user: CurrentUser = Depends(get_current_user),
    service: OptimizerService = Depends(get_optimizer_service),
) -> OptimizationRunResponse:
    """Grid Search submit — 202 + OptimizationRun row."""
    _ = request
    return await service.submit_grid_search(data, user_id=user.id)


@router.get("/runs/{run_id}", response_model=OptimizationRunResponse)
async def get_optimization_run(
    run_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: OptimizerService = Depends(get_optimizer_service),
) -> OptimizationRunResponse:
    """OptimizationRun 단일 조회 (소유자 격리)."""
    return await service.get(run_id, user_id=user.id)


@router.get("/runs", response_model=Page[OptimizationRunResponse])
async def list_optimization_runs(
    user: CurrentUser = Depends(get_current_user),
    service: OptimizerService = Depends(get_optimizer_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    backtest_id: UUID | None = Query(None),
) -> Page[OptimizationRunResponse]:
    """소유자 격리된 페이지네이션 list (생성 역순)."""
    return await service.list(
        user_id=user.id, limit=limit, offset=offset, backtest_id=backtest_id
    )

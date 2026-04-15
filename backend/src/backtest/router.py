"""Backtest REST API — 7 endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.backtest.dependencies import get_backtest_service
from src.backtest.schemas import (
    BacktestCancelResponse,
    BacktestCreatedResponse,
    BacktestDetail,
    BacktestProgressResponse,
    BacktestSummary,
    CreateBacktestRequest,
    TradeItem,
)
from src.backtest.service import BacktestService
from src.common.pagination import Page

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", response_model=BacktestCreatedResponse, status_code=202)
async def submit_backtest(
    data: CreateBacktestRequest,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestCreatedResponse:
    return await service.submit(data, user_id=user.id)


@router.get("", response_model=Page[BacktestSummary])
async def list_backtests(
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Page[BacktestSummary]:
    return await service.list(user_id=user.id, limit=limit, offset=offset)


@router.get("/{backtest_id}", response_model=BacktestDetail)
async def get_backtest(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestDetail:
    return await service.get(backtest_id, user_id=user.id)


@router.get("/{backtest_id}/trades", response_model=Page[TradeItem])
async def list_backtest_trades(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[TradeItem]:
    return await service.list_trades(
        backtest_id, user_id=user.id, limit=limit, offset=offset
    )


@router.get("/{backtest_id}/progress", response_model=BacktestProgressResponse)
async def get_backtest_progress(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestProgressResponse:
    return await service.progress(backtest_id, user_id=user.id)


@router.post(
    "/{backtest_id}/cancel",
    response_model=BacktestCancelResponse,
    status_code=202,
)
async def cancel_backtest(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestCancelResponse:
    return await service.cancel(backtest_id, user_id=user.id)


@router.delete("/{backtest_id}", status_code=204)
async def delete_backtest(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> Response:
    await service.delete(backtest_id, user_id=user.id)
    return Response(status_code=204)

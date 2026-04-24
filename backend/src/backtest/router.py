"""Backtest REST API — 7 endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response

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
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> BacktestCreatedResponse:
    """POST /backtests.

    Sprint 9-6 E2: Idempotency-Key + 동일 body → `replayed=True` 반환 +
    응답 헤더 `X-Idempotency-Replayed: true`. 상태 코드는 replay/신규 모두
    202 유지 ("Accepted" 의미 — 신규 or 기존 queued 둘 다 async).
    """
    result = await service.submit(
        data, user_id=user.id, idempotency_key=idempotency_key
    )
    if result.replayed:
        response.headers["X-Idempotency-Replayed"] = "true"
    return result


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
) -> None:
    await service.delete(backtest_id, user_id=user.id)

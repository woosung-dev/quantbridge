"""strategy HTTP 라우터."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.strategy.dependencies import get_strategy_service
from src.strategy.models import ParseStatus
from src.strategy.schemas import (
    CreateStrategyRequest,
    ParsePreviewResponse,
    ParseRequest,
    StrategyListResponse,
    StrategyResponse,
)
from src.strategy.service import StrategyService

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/parse", response_model=ParsePreviewResponse)
async def parse_preview(
    data: ParseRequest,
    _current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> ParsePreviewResponse:
    return await service.parse_preview(data.pine_source)


@router.post("", status_code=201, response_model=StrategyResponse)
async def create_strategy(
    data: CreateStrategyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.create(data, owner_id=current_user.id)


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    parse_status: ParseStatus | None = Query(None),
    is_archived: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyListResponse:
    return await service.list(
        owner_id=current_user.id,
        page=page,
        limit=limit,
        parse_status=parse_status,
        is_archived=is_archived,
    )

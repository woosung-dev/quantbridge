"""strategy HTTP 라우터."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

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
    UpdateStrategyRequest,
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


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.get(strategy_id=strategy_id, owner_id=current_user.id)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    data: UpdateStrategyRequest,
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.update(
        strategy_id=strategy_id, owner_id=current_user.id, data=data
    )


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> None:
    await service.delete(strategy_id=strategy_id, owner_id=current_user.id)

"""strategy HTTP 라우터."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.strategy.dependencies import get_strategy_service
from src.strategy.schemas import ParsePreviewResponse, ParseRequest
from src.strategy.service import StrategyService

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/parse", response_model=ParsePreviewResponse)
async def parse_preview(
    data: ParseRequest,
    _current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> ParsePreviewResponse:
    return await service.parse_preview(data.pine_source)

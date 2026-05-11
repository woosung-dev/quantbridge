# POST /api/v1/strategies/convert-indicator — indicator → strategy 변환
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.strategy.convert.dependencies import get_convert_service
from src.strategy.convert.schemas import ConvertIndicatorRequest, ConvertIndicatorResponse
from src.strategy.convert.service import ConvertService

router = APIRouter(prefix="/strategies", tags=["indicator-convert"])


@router.post("/convert-indicator", response_model=ConvertIndicatorResponse)
@limiter.limit("5/minute")
def convert_indicator(
    request: Request,
    req: ConvertIndicatorRequest,
    _: CurrentUser = Depends(get_current_user),
    svc: ConvertService = Depends(get_convert_service),
) -> ConvertIndicatorResponse:
    try:
        return svc.convert(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

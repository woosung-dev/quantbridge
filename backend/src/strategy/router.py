"""strategy HTTP 라우터.

T19: rotate-webhook-secret endpoint 추가 (ownership은 StrategyService.get으로 검증).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.core.config import settings
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
from src.trading.dependencies import get_webhook_secret_service
from src.trading.schemas import WebhookRotateResponse
from src.trading.service import WebhookSecretService

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/parse", response_model=ParsePreviewResponse)
async def parse_preview(
    data: ParseRequest,
    _current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> ParsePreviewResponse:
    return await service.parse_preview(data.pine_source)


@router.post("", status_code=201, response_model=StrategyResponse)
@limiter.limit("30/minute")
async def create_strategy(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: CreateStrategyRequest,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.create(data, owner_id=current_user.id)


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    page: int | None = Query(
        None,
        ge=1,
        deprecated=True,
        description="Deprecated: use offset (= (page-1)*limit). Sprint 6+ 제거 예정.",
    ),
    parse_status: ParseStatus | None = Query(None),
    is_archived: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyListResponse:
    # legacy 호환: page가 들어오면 offset으로 변환
    effective_offset = (page - 1) * limit if page is not None else offset
    return await service.list(
        owner_id=current_user.id,
        limit=limit,
        offset=effective_offset,
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


# ── Webhook Secret Rotation (T19) ────────────────────────────────────


@router.post(
    "/{strategy_id}/rotate-webhook-secret",
    response_model=WebhookRotateResponse,
)
async def rotate_webhook_secret(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    strategy_svc: StrategyService = Depends(get_strategy_service),
    secret_svc: WebhookSecretService = Depends(get_webhook_secret_service),
) -> WebhookRotateResponse:
    """Rotate the webhook secret for a strategy.

    Ownership check via StrategyService.get (raises 404 if not owner).
    """
    # Ownership check — raises StrategyNotFoundError (404) if not owner
    await strategy_svc.get(strategy_id=strategy_id, owner_id=current_user.id)

    plaintext = await secret_svc.rotate(
        strategy_id,
        grace_period_seconds=settings.webhook_secret_grace_seconds,
    )
    webhook_url = f"/api/v1/webhooks/{strategy_id}?token={{HMAC}}"
    return WebhookRotateResponse(secret=plaintext, webhook_url=webhook_url)

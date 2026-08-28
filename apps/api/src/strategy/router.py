"""strategy HTTP 라우터.

T19: rotate-webhook-secret endpoint 추가 (ownership은 StrategyService.get으로 검증).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.core.config import settings
from src.strategy.dependencies import get_strategy_service
from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus
from src.strategy.narrative.catalog import ModelNotAvailableError, resolve_override
from src.strategy.narrative.dependencies import get_generate_service
from src.strategy.narrative.generate_service import GenerateService
from src.strategy.narrative.schemas import (
    GenerateStrategyRequest,
    GenerateStrategyResponse,
    StrategyNarrativeResponse,
)
from src.strategy.schemas import (
    CreateStrategyRequest,
    ParsePreviewResponse,
    ParseRequest,
    StrategyBriefResponse,
    StrategyCreateResponse,
    StrategyListResponse,
    StrategyResponse,
    StrategySettings,
    UpdateStrategyRequest,
    UpdateStrategySettingsRequest,
)
from src.strategy.service import StrategyService
from src.trading.dependencies import get_webhook_secret_service
from src.trading.schemas import WebhookRotateResponse
from src.trading.services.webhook_secret_service import WebhookSecretService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _opaque(status_code: int, code: str, message: str, exc: Exception) -> HTTPException:
    """[BL-772] 예외 상세를 응답에서 지우고 **로그와 잇는 상관 ID** 만 남긴다.

    `convert/router.py:_opaque` 와 같은 계약이다 — 지우기만 하면 사용자 문의를 추적할 수 없어
    `error_id` 가 그 대가를 상쇄한다.
    """
    error_id = uuid4().hex[:12]
    logger.exception("%s error_id=%s exc_type=%s", code, error_id, type(exc).__name__)
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "detail": message, "error_id": error_id},
    )


@router.post("/parse", response_model=ParsePreviewResponse)
async def parse_preview(
    data: ParseRequest,
    _current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> ParsePreviewResponse:
    return await service.parse_preview(data.pine_source)


@router.post("", status_code=201, response_model=StrategyCreateResponse)
@limiter.limit("30/minute")
async def create_strategy(
    request: Request,  # slowapi 가 IP/key 추출에 사용
    data: CreateStrategyRequest,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyCreateResponse:
    """Sprint 13 Phase A.1.4: response 에 webhook_secret plaintext 1회 포함.

    Frontend 가 sessionStorage 캐시 (TTL 30분) 로 후속 Test Order Dialog 에서 재사용.
    GET / list 응답은 StrategyResponse 유지 — webhook_secret 노출 X.
    """
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
    order_by: Literal["updated_at", "name", "total_return", "sharpe_ratio"] = Query("updated_at"),
    order: Literal["asc", "desc"] = Query("desc"),
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
        order_by=order_by,
        order=order,
    )


@router.post("/generate", response_model=GenerateStrategyResponse)
@limiter.limit("5/minute")
async def generate_strategy(
    request: Request,
    req: GenerateStrategyRequest,
    _: CurrentUser = Depends(get_current_user),
    svc: GenerateService = Depends(get_generate_service),
) -> GenerateStrategyResponse:
    """[ADR-041] 자연어 → 전략 생성. **저장하지 않는다.**

    ★산출물만 돌려주고 사용자가 검토한 뒤 기존 생성 흐름으로 저장한다(`convert` 선례) —
    이 엔드포인트가 DB 를 안 쥐는 이유이고, 검토 없이 저장되는 경로를 만들지 않는 이유다.
    ★판정(`is_runnable`·`unsupported`)은 LLM 이 아니라 `analyze_coverage` 가 낸다.
    """
    try:
        return await asyncio.to_thread(svc.generate, req)
    except RuntimeError as exc:
        raise _opaque(
            503,
            "generate_provider_unavailable",
            "전략 생성 provider 를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
            exc,
        ) from exc
    except Exception as exc:
        raise _opaque(
            502,
            "generate_failed",
            "전략 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
            exc,
        ) from exc


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.get(strategy_id=strategy_id, owner_id=current_user.id)


@router.get("/{strategy_id}/brief", response_model=StrategyBriefResponse)
async def get_strategy_brief(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyBriefResponse:
    """[ADR-040] 백테스트 제출 전 결정론 브리핑 — LLM 이 만든 값이 하나도 없다."""
    return await service.brief(strategy_id=strategy_id, owner_id=current_user.id)


@router.get("/{strategy_id}/brief/narrative", response_model=StrategyNarrativeResponse)
@limiter.limit("10/minute")
async def get_strategy_brief_narrative(
    request: Request,
    strategy_id: UUID = Path(...),
    provider: str | None = Query(default=None, max_length=32),
    model: str | None = Query(default=None, max_length=128),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyNarrativeResponse:
    """[ADR-040] 해설 층 — **판정하지 않는다.** 실패해도 `/brief` 로 화면이 완결된다.

    ★`provider`+`model` 은 **함께** 주는 선택 파라미터다(`GET /api/v1/llm/models` 의 목록에서 고른다).
      안 주면 `LLM_PROVIDER_ORDER` 가 정한 기본이 돈다.
    ★검증은 **왕복 전에** 한다 — 폐기·오타 모델을 그대로 보내면 404 가 503 으로 둔갑해 원인이 지워진다.
    """
    try:
        effective = await asyncio.to_thread(
            resolve_override, settings, provider=provider, model=model
        )
    except ModelNotAvailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "llm_model_not_available", "detail": str(exc)},
        ) from exc
    try:
        return await service.brief_narrative(
            strategy_id=strategy_id, owner_id=current_user.id, settings_override=effective
        )
    except StrategyNotFoundError:
        raise
    except RuntimeError as exc:
        # ★[BL-772] 계약 — SDK 예외 문자열을 응답에 싣지 않고 상관 ID 만 남긴다.
        raise _opaque(
            503,
            "narrative_provider_unavailable",
            "전략 해설을 만들 수 없습니다. 잠시 후 다시 시도해 주세요.",
            exc,
        ) from exc
    except Exception as exc:
        raise _opaque(
            502,
            "narrative_failed",
            "전략 해설 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
            exc,
        ) from exc


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    data: UpdateStrategyRequest,
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.update(strategy_id=strategy_id, owner_id=current_user.id, data=data)


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> None:
    await service.delete(strategy_id=strategy_id, owner_id=current_user.id)


@router.put("/{strategy_id}/settings", response_model=StrategyResponse)
async def update_strategy_settings(
    data: UpdateStrategySettingsRequest,
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    """Sprint 26 — Live Signal Auto-Trading prereq.

    leverage / margin_mode / position_size_pct 저장. Live Session register 시
    StrategySettings.model_validate 가 read path validation (codex G.0 P2 #4).
    """
    settings = StrategySettings(**data.model_dump())
    return await service.update_settings(
        strategy_id=strategy_id, owner_id=current_user.id, settings=settings
    )


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

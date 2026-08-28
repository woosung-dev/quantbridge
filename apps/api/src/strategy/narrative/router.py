# GET /api/v1/llm/models — provider 별 **살아 있는** 모델 목록 + 설정값 드리프트
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Request

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.core.config import settings
from src.strategy.narrative import catalog as catalog_mod
from src.strategy.narrative.providers import available_providers
from src.strategy.narrative.schemas import (
    LlmModelItem,
    LlmModelsResponse,
    LlmProviderModels,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/models", response_model=LlmModelsResponse)
@limiter.limit("20/minute")
async def list_llm_models(
    request: Request,
    _: CurrentUser = Depends(get_current_user),
) -> LlmModelsResponse:
    """provider 3종의 모델 목록을 **물어서** 돌려준다.

    ★provider 하나가 죽어도 **나머지는 나온다** — 실패는 그 provider 의 `error` 로 실린다.
    ★목록을 못 읽었을 때 `configured_listed` 는 `False` 가 아니라 **`None`**(모른다)이다.
      「없다」와 「못 봤다」를 같은 값으로 접으면 멀쩡한 설정을 오경보한다.
    ★SDK 호출이 동기라 스레드로 뺀다 — 이벤트 루프를 세 번 왕복만큼 막지 않는다.
    """
    cats = await asyncio.to_thread(catalog_mod.catalog, settings)
    avail = available_providers(settings)
    return LlmModelsResponse(
        providers=[
            LlmProviderModels(
                provider=c.provider,
                models=[LlmModelItem(**vars(m)) for m in c.models],
                total_seen=c.total_seen,
                configured=c.configured,
                configured_listed=c.configured_listed,
                error=c.error,
            )
            for c in cats
        ],
        order=[c.provider for c in cats],
        active=avail[0] if avail else None,
    )

# POST /api/v1/strategies/convert-indicator — indicator → strategy 변환
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.strategy.convert.dependencies import get_convert_service
from src.strategy.convert.schemas import ConvertIndicatorRequest, ConvertIndicatorResponse
from src.strategy.convert.service import ConvertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["indicator-convert"])


def _opaque(status_code: int, code: str, message: str, exc: Exception) -> HTTPException:
    """[BL-772] 예외 상세를 응답에서 지우고 **로그와 잇는 상관 ID** 만 남긴다.

    ★지우기만 하면 사용자 문의를 추적할 수 없다 — `error_id` 가 그 대가를 상쇄한다.
    본문 모양은 레포 관례(`common/exceptions.AppException`)와 같은 `{"code", "detail"}` 이다.
    """
    error_id = uuid4().hex[:12]
    logger.exception("%s error_id=%s exc_type=%s", code, error_id, type(exc).__name__)
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "detail": message, "error_id": error_id},
    )


@router.post("/convert-indicator", response_model=ConvertIndicatorResponse)
@limiter.limit("5/minute")
def convert_indicator(
    request: Request,
    req: ConvertIndicatorRequest,
    response: Response,
    _: CurrentUser = Depends(get_current_user),
    svc: ConvertService = Depends(get_convert_service),
) -> ConvertIndicatorResponse:
    try:
        return svc.convert(req)
    except RuntimeError as exc:
        raise _opaque(
            503,
            "llm_provider_unavailable",
            "LLM 변환 provider 를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
            exc,
        ) from exc
    except Exception as exc:
        raise _opaque(
            502,
            "llm_convert_failed",
            "LLM 변환에 실패했습니다. 잠시 후 다시 시도해 주세요.",
            exc,
        ) from exc

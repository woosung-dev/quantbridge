"""auth HTTP 라우터."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from svix.webhooks import Webhook, WebhookVerificationError

from src.auth.dependencies import get_current_user, get_user_service
from src.auth.exceptions import WebhookSignatureError
from src.auth.schemas import CurrentUser, UserResponse
from src.auth.service import UserService
from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _svix_webhook() -> Webhook:
    """모듈 스코프 싱글톤 회피 — 테스트 monkeypatch 용이."""
    return Webhook(settings.clerk_webhook_secret.get_secret_value())


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.user_repo.find_by_id(current_user.id)
    assert user is not None  # dependency가 보장
    return UserResponse.model_validate(user)


@router.post("/webhook", status_code=200)
async def clerk_webhook(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, bool]:
    """Clerk Svix-signed webhook 수신."""
    payload = await request.body()  # raw bytes 필수
    headers = {k.lower(): v for k, v in request.headers.items()}

    wh = _svix_webhook()
    try:
        event = wh.verify(payload, headers)
    except (WebhookVerificationError, ValueError) as exc:
        # WebhookVerificationError: 서명 불일치
        # ValueError (binascii.Error 포함): 잘못된 base64 포맷
        raise WebhookSignatureError() from exc

    # verify 반환값이 dict 혹은 bytes일 수 있음. 안전하게 json 로드.
    if isinstance(event, bytes):
        event = json.loads(event)

    await service.handle_clerk_event(event)
    return {"received": True}

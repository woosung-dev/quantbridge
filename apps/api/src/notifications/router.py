"""notifications HTTP 라우터 — `/api/v1/push/*` (pwa.md §3.2). 전부 인증 필수."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.notifications.dependencies import get_push_service
from src.notifications.schemas import (
    CreatePushSubscriptionRequest,
    DeletePushSubscriptionRequest,
    PushConfigResponse,
    PushSubscriptionResponse,
    PushTestResponse,
)
from src.notifications.service import PushNotificationService

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/config", response_model=PushConfigResponse)
async def get_push_config(
    _user: CurrentUser = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_service),
) -> PushConfigResponse:
    return service.get_config()


@router.post(
    "/subscriptions",
    status_code=status.HTTP_201_CREATED,
    response_model=PushSubscriptionResponse,
    responses={200: {"model": PushSubscriptionResponse, "description": "기존 구독 갱신(upsert)"}},
)
async def subscribe(
    data: CreatePushSubscriptionRequest,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_service),
) -> PushSubscriptionResponse:
    subscription, created = await service.subscribe(current_user.id, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return subscription


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    data: DeletePushSubscriptionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_service),
) -> Response:
    await service.unsubscribe(current_user.id, data.endpoint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=PushTestResponse)
async def send_test_push(
    current_user: CurrentUser = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_service),
) -> PushTestResponse:
    return await service.send_test(current_user.id)

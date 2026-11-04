"""notifications HTTP 라우터 — `/api/v1/push/*` (pwa.md §3.2). 전부 인증 필수."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from src.auth.dependencies import CurrentUserDep
from src.notifications.dependencies import PushServiceDep
from src.notifications.schemas import (
    CreatePushSubscriptionRequest,
    DeletePushSubscriptionRequest,
    PushConfigResponse,
    PushSubscriptionResponse,
    PushTestResponse,
)

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/config")
async def get_push_config(
    _user: CurrentUserDep,
    service: PushServiceDep,
) -> PushConfigResponse:
    return service.get_config()


@router.post(
    "/subscriptions",
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": PushSubscriptionResponse, "description": "기존 구독 갱신(upsert)"}},
)
async def subscribe(
    data: CreatePushSubscriptionRequest,
    response: Response,
    current_user: CurrentUserDep,
    service: PushServiceDep,
) -> PushSubscriptionResponse:
    subscription, created = await service.subscribe(current_user.id, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return subscription


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    data: DeletePushSubscriptionRequest,
    current_user: CurrentUserDep,
    service: PushServiceDep,
) -> Response:
    await service.unsubscribe(current_user.id, data.endpoint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test")
async def send_test_push(
    current_user: CurrentUserDep,
    service: PushServiceDep,
) -> PushTestResponse:
    return await service.send_test(current_user.id)

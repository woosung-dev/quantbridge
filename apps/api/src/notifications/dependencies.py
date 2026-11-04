"""notifications Depends() 조립."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.notifications.repository import PushSubscriptionRepository
from src.notifications.service import PushNotificationService
from src.notifications.webpush_client import (
    PushSender,
    VapidConfig,
    load_vapid_config,
    send_webpush,
)


async def get_push_subscription_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PushSubscriptionRepository:
    return PushSubscriptionRepository(session)


def get_vapid_config() -> VapidConfig | None:
    return load_vapid_config()


def get_push_sender() -> PushSender:
    """테스트는 이 factory 를 override 해 실제 푸시 서비스로 나가지 않는다."""
    return send_webpush


async def get_push_service(
    repo: Annotated[PushSubscriptionRepository, Depends(get_push_subscription_repository)],
    vapid: Annotated[VapidConfig | None, Depends(get_vapid_config)],
    sender: Annotated[PushSender, Depends(get_push_sender)],
) -> PushNotificationService:
    return PushNotificationService(repo=repo, vapid=vapid, sender=sender)


# 라우터에서 반복되는 서비스 주입 별칭.
PushServiceDep = Annotated[PushNotificationService, Depends(get_push_service)]


def build_push_service_for_worker(session: AsyncSession) -> PushNotificationService:
    """Celery `notifications.send_push` 용 — Request 없이 같은 조립."""
    return PushNotificationService(
        repo=PushSubscriptionRepository(session),
        vapid=load_vapid_config(),
        sender=send_webpush,
    )

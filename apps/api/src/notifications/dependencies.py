"""notifications Depends() 조립."""

from __future__ import annotations

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
    session: AsyncSession = Depends(get_async_session),
) -> PushSubscriptionRepository:
    return PushSubscriptionRepository(session)


def get_vapid_config() -> VapidConfig | None:
    return load_vapid_config()


def get_push_sender() -> PushSender:
    """테스트는 이 factory 를 override 해 실제 푸시 서비스로 나가지 않는다."""
    return send_webpush


async def get_push_service(
    repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
    vapid: VapidConfig | None = Depends(get_vapid_config),
    sender: PushSender = Depends(get_push_sender),
) -> PushNotificationService:
    return PushNotificationService(repo=repo, vapid=vapid, sender=sender)


def build_push_service_for_worker(session: AsyncSession) -> PushNotificationService:
    """Celery `notifications.send_push` 용 — Request 없이 같은 조립."""
    return PushNotificationService(
        repo=PushSubscriptionRepository(session),
        vapid=load_vapid_config(),
        sender=send_webpush,
    )

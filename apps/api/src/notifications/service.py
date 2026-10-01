"""notifications Service — 구독 upsert/해제 + 발송 (pwa.md §3.2 · §3.4)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.notifications.dispatcher import TEST_PUSH_PAYLOAD, PushPayload
from src.notifications.exceptions import PushDisabledError, PushSubscriptionNotFoundError
from src.notifications.models import PushSubscription
from src.notifications.repository import PushSubscriptionRepository
from src.notifications.schemas import (
    CreatePushSubscriptionRequest,
    PushConfigResponse,
    PushSubscriptionResponse,
    PushTestResponse,
)
from src.notifications.webpush_client import PushSender, VapidConfig

logger = logging.getLogger(__name__)

# 푸시 서비스가 「이 구독은 없다/만료됐다」고 답하는 코드 — 그 구독은 지운다.
_GONE_STATUSES = frozenset({404, 410})


@dataclass(frozen=True)
class PushSendResult:
    sent: int
    removed: int


class PushNotificationService:
    def __init__(
        self,
        *,
        repo: PushSubscriptionRepository,
        vapid: VapidConfig | None,
        sender: PushSender,
    ) -> None:
        self.repo = repo
        self.vapid = vapid
        self.sender = sender

    def get_config(self) -> PushConfigResponse:
        if self.vapid is None:
            return PushConfigResponse(enabled=False, public_key=None)
        return PushConfigResponse(enabled=True, public_key=self.vapid.public_key)

    async def subscribe(
        self, user_id: UUID, data: CreatePushSubscriptionRequest
    ) -> tuple[PushSubscriptionResponse, bool]:
        """upsert. 반환 bool = 새로 만들었는가(201) / 기존 행을 갱신했는가(200).

        같은 endpoint 가 다른 사용자로 오면 그 행을 **현재 사용자로 재할당**한다(공용 기기).
        """
        existing = await self.repo.find_by_endpoint(data.endpoint)
        if existing is None:
            try:
                created = await self.repo.create(
                    PushSubscription(
                        user_id=user_id,
                        endpoint=data.endpoint,
                        p256dh=data.keys.p256dh,
                        auth=data.keys.auth,
                        user_agent=data.user_agent,
                    )
                )
                await self.repo.commit()
                return PushSubscriptionResponse.model_validate(created), True
            except IntegrityError:
                # 같은 endpoint 의 동시 구독이 먼저 INSERT 했다 → 그 행을 갱신한다.
                await self.repo.rollback()
                existing = await self.repo.find_by_endpoint(data.endpoint)
                if existing is None:
                    raise
        updated = await self.repo.reassign(
            existing,
            user_id=user_id,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth,
            user_agent=data.user_agent,
        )
        await self.repo.commit()
        return PushSubscriptionResponse.model_validate(updated), False

    async def unsubscribe(self, user_id: UUID, endpoint: str) -> None:
        subscription = await self.repo.find_by_endpoint(endpoint)
        if subscription is None or subscription.user_id != user_id:
            raise PushSubscriptionNotFoundError()
        await self.repo.delete(subscription)
        await self.repo.commit()

    async def send_push(self, user_id: UUID, payload: PushPayload) -> PushSendResult:
        """사용자 구독 전부에 발송. 404·410 → 구독 삭제 · 2xx → `last_success_at` · 그 외 → 로그만."""
        if self.vapid is None:
            return PushSendResult(sent=0, removed=0)
        subscriptions = await self.repo.list_by_user(user_id)
        if not subscriptions:
            return PushSendResult(sent=0, removed=0)

        data = json.dumps(payload, ensure_ascii=False)
        sent = 0
        removed = 0
        for subscription in subscriptions:
            info = {
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            }
            try:
                status_code = await self.sender(info, data, self.vapid)
            except Exception:
                logger.warning("push_send_error subscription_id=%s", subscription.id, exc_info=True)
                continue
            if status_code in _GONE_STATUSES:
                await self.repo.delete(subscription)
                removed += 1
            elif 200 <= status_code < 300:
                await self.repo.mark_success(subscription, at=datetime.now(UTC))
                sent += 1
            else:
                logger.warning(
                    "push_send_rejected subscription_id=%s status=%s",
                    subscription.id,
                    status_code,
                )
        await self.repo.commit()
        return PushSendResult(sent=sent, removed=removed)

    async def send_test(self, user_id: UUID) -> PushTestResponse:
        if self.vapid is None:
            raise PushDisabledError()
        result = await self.send_push(user_id, TEST_PUSH_PAYLOAD)
        return PushTestResponse(sent=result.sent, removed=result.removed)

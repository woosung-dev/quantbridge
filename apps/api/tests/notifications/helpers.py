"""notifications 테스트 공용 — 가짜 발신기 · VAPID 상수 · 구독 시드."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.models import PushSubscription
from src.notifications.webpush_client import VapidConfig

VAPID = VapidConfig(
    public_key="BTestPublicKey-base64url",
    private_key="test-private-key-base64url",
    subject="mailto:push-test@example.com",
)

ENDPOINT_A = "https://fcm.googleapis.com/fcm/send/endpoint-a"
ENDPOINT_B = "https://updates.push.services.mozilla.com/wpush/v2/endpoint-b"
ENDPOINT_C = "https://web.push.apple.com/endpoint-c"


def subscribe_body(endpoint: str, *, user_agent: str | None = "pytest-ua") -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": f"p256dh-{endpoint[-1]}", "auth": f"auth-{endpoint[-1]}"},
        "user_agent": user_agent,
    }


class FakeSender:
    """endpoint → 상태 코드(또는 예외). 실제 푸시 서비스로 나가지 않는다."""

    def __init__(self, outcomes: dict[str, int | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, info: dict[str, Any], data: str, vapid: VapidConfig) -> int:
        self.calls.append((info["endpoint"], json.loads(data)))
        outcome = self.outcomes[info["endpoint"]]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def seed_subscription(
    session: AsyncSession, user_id: UUID, endpoint: str
) -> PushSubscription:
    subscription = PushSubscription(
        user_id=user_id,
        endpoint=endpoint,
        p256dh="p256dh-seed",
        auth="auth-seed",
        user_agent="seed-ua",
    )
    session.add(subscription)
    await session.flush()
    return subscription

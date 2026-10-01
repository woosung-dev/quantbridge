"""VAPID 설정 + pywebpush 발신 (pwa.md §3.3 · §3.4).

★발신 함수는 `PushSender` 로 **주입**된다 — 테스트는 실제 푸시 서비스로 네트워크를 타지 않는다.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pywebpush import WebPushException, webpush

from src.core.config import settings

# pwa.md §3.4 — 푸시 서비스 왕복 상한.
PUSH_TIMEOUT_SECONDS = 10.0
# pywebpush 기본 TTL 은 0(「지금 못 전하면 버려라」)이라 잠든 기기는 알림을 영영 못 받는다.
# 하루를 준다 — 같은 `tag` 는 기기에서 하나로 합쳐지므로 늦게 와도 중복으로 쌓이지 않는다.
PUSH_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class VapidConfig:
    public_key: str
    private_key: str = field(repr=False)
    subject: str


# (subscription_info, data, vapid) → 푸시 서비스 HTTP 상태 코드. 네트워크 오류는 raise.
PushSender = Callable[[dict[str, Any], str, VapidConfig], Awaitable[int]]


def load_vapid_config() -> VapidConfig | None:
    """VAPID 3종이 전부 있을 때만 설정을 돌려준다 — 하나라도 없으면 푸시는 꺼진 것이다."""
    public_key = settings.vapid_public_key
    private_key = settings.vapid_private_key
    subject = settings.vapid_subject
    if not public_key or private_key is None or not subject:
        return None
    return VapidConfig(
        public_key=public_key,
        private_key=private_key.get_secret_value(),
        subject=subject,
    )


def _send_sync(subscription_info: dict[str, Any], data: str, vapid: VapidConfig) -> int:
    try:
        response = webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=vapid.private_key,
            # ★호출마다 새 dict — pywebpush 가 claims 에 `aud`(endpoint origin)·`exp` 를 **써 넣는다**.
            #   `aud` 는 비어 있을 때만 채우므로(pywebpush 2.3.0 소스), dict 를 재사용하면 첫
            #   endpoint 의 origin 이 다른 푸시 서비스로 따라가 JWT 가 거부된다.
            vapid_claims={"sub": vapid.subject},
            timeout=PUSH_TIMEOUT_SECONDS,
            ttl=PUSH_TTL_SECONDS,
        )
    except WebPushException as exc:
        if exc.response is not None:
            return int(exc.response.status_code)
        raise
    return int(response.status_code)


async def send_webpush(subscription_info: dict[str, Any], data: str, vapid: VapidConfig) -> int:
    """실 발신 — `webpush` 는 동기(requests)라 스레드로 넘긴다."""
    return await asyncio.to_thread(_send_sync, subscription_info, data, vapid)

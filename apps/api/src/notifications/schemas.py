"""notifications 도메인 Pydantic V2 스키마 (pwa.md §3.2)."""

from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

# 브라우저 `PushSubscription.endpoint` 는 전부 https 다.
_ENDPOINT_FIELD = Field(min_length=9, max_length=2048, pattern=r"^https://")

# ★서버가 구독 endpoint 로 POST 한다. API 는 Access 밖이고 가입이 열려 있어, https 만 막으면
#   내부 https 호스트로 요청을 보내고 `/push/test` 의 `{sent, removed}` 로 응답을 엿보는 SSRF
#   오라클이 남는다 → 등록 입구에서 **알려진 푸시 서비스 호스트만** 받는다(코드 상수 — env 아님).
#   Chromium 계열 = FCM · Firefox = Mozilla autopush · Safari = Apple · Edge(레거시) = WNS.
_PUSH_SERVICE_HOSTS = frozenset({"fcm.googleapis.com", "updates.push.services.mozilla.com"})
_PUSH_SERVICE_HOST_SUFFIXES = (".push.apple.com", ".notify.windows.com")


def _is_allowed_push_endpoint(endpoint: str) -> bool:
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError:
        return False
    host = parts.hostname or ""
    if parts.scheme != "https" or parts.username is not None or port not in (None, 443):
        return False
    return host in _PUSH_SERVICE_HOSTS or host.endswith(_PUSH_SERVICE_HOST_SUFFIXES)


class PushConfigResponse(BaseModel):
    """GET /push/config — VAPID 3종 중 하나라도 없으면 `enabled: false, public_key: null`."""

    enabled: bool
    public_key: str | None


class PushSubscriptionKeys(BaseModel):
    """브라우저 `subscription.toJSON().keys`."""

    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class CreatePushSubscriptionRequest(BaseModel):
    """POST /push/subscriptions — `subscription.toJSON()` + `user_agent`."""

    endpoint: str = _ENDPOINT_FIELD
    keys: PushSubscriptionKeys
    user_agent: str | None = Field(default=None, max_length=512)

    @field_validator("endpoint")
    @classmethod
    def _endpoint_must_be_push_service(cls, v: str) -> str:
        if not _is_allowed_push_endpoint(v):
            raise ValueError("endpoint host is not an allowed web push service")
        return v


class DeletePushSubscriptionRequest(BaseModel):
    """DELETE /push/subscriptions body — 발송하지 않으므로 호스트 허용 목록 없이 https 만 본다."""

    endpoint: str = _ENDPOINT_FIELD


class PushSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    endpoint: str
    created_at: AwareDatetime


class PushTestResponse(BaseModel):
    """POST /push/test — 성공 발송 수 · 만료(404/410)로 지운 구독 수."""

    sent: int
    removed: int

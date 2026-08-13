"""Sprint 11 Phase A — Clerk webhook country_code 검증 + 저장.

3 계층 geo-block 중 L3 (서명검증된 Clerk webhook 의 public_metadata.country).
L1 (Cloudflare WAF) + L2 (Next.js proxy.ts) 는 별도 계층.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from src.auth.repository import UserRepository
from src.core.config import settings


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """테스트용 고정 Svix 시크릿."""
    from base64 import b64encode

    raw = b"a" * 32
    secret = "whsec_" + b64encode(raw).decode()
    monkeypatch.setattr(settings, "clerk_webhook_secret", SecretStr(secret))
    return secret


def _headers_with_signature(secret: str, body: bytes) -> dict[str, str]:
    """svix SDK 의 sign() 으로 유효 헤더 3종 생성."""
    from svix.webhooks import Webhook as SvixWebhook

    msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    timestamp = datetime.fromtimestamp(int(time.time()), tz=UTC)
    wh = SvixWebhook(secret)
    signature = wh.sign(
        msg_id=msg_id,
        timestamp=timestamp,
        data=body.decode(),
    )
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
    }


def _clerk_user_created_payload(clerk_id: str, country: str | None) -> bytes:
    """user.created 이벤트 바디. country 는 public_metadata 에 주입."""
    public_metadata: dict[str, object] = {}
    if country is not None:
        public_metadata["country"] = country
    return json.dumps(
        {
            "type": "user.created",
            "data": {
                "id": clerk_id,
                "email_addresses": [{"id": "e1", "email_address": "u@example.com"}],
                "primary_email_address_id": "e1",
                "username": "u",
                "public_metadata": public_metadata,
            },
        }
    ).encode()


@pytest.mark.asyncio
async def test_clerk_webhook_rejects_restricted_country(client, webhook_secret):
    """US 국가 코드 가입 시도는 400 geo_blocked_country 로 거절."""
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    body = _clerk_user_created_payload(clerk_id, country="US")
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 400, res.text
    assert res.json()["detail"]["code"] == "geo_blocked_country"


@pytest.mark.asyncio
async def test_clerk_webhook_accepts_allowed_country(client, db_session, webhook_secret):
    """KR 국가 코드 가입은 정상 200 수용."""
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    body = _clerk_user_created_payload(clerk_id, country="KR")
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json() == {"received": True}


@pytest.mark.asyncio
async def test_country_code_persisted_on_signup(client, db_session, webhook_secret):
    """허용 국가의 country_code 는 users 테이블에 저장."""
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    body = _clerk_user_created_payload(clerk_id, country="KR")
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200, res.text

    repo = UserRepository(db_session)
    user = await repo.find_by_clerk_id(clerk_id)
    assert user is not None
    assert user.country_code == "KR"


@pytest.mark.asyncio
async def test_country_code_missing_is_accepted_and_null(client, db_session, webhook_secret):
    """country 정보가 없는 payload 는 null 저장으로 수용 (기존 계정 마이그레이션 호환)."""
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    body = _clerk_user_created_payload(clerk_id, country=None)
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200, res.text

    repo = UserRepository(db_session)
    user = await repo.find_by_clerk_id(clerk_id)
    assert user is not None
    assert user.country_code is None

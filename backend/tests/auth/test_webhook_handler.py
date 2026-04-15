"""/api/v1/auth/webhook Svix 서명 검증 E2E."""
from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from src.auth.repository import UserRepository
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """테스트용 고정 Svix 시크릿. whsec_<base64> 형식 (32-byte raw key)."""
    from base64 import b64encode

    raw = b"a" * 32
    secret = "whsec_" + b64encode(raw).decode()
    monkeypatch.setattr(settings, "clerk_webhook_secret", SecretStr(secret))
    return secret


def _headers_with_signature(secret: str, body: bytes) -> dict[str, str]:
    """svix SDK의 sign()을 사용해 유효 헤더 3종 생성.

    svix Webhook.sign(msg_id, timestamp, data) — timestamp는 datetime 타입 필요.
    sign() 내부에서 timestamp.replace(tzinfo=utc).timestamp() 사용하므로
    UTC aware datetime을 전달해야 epoch 값이 일치한다.
    """
    from svix.webhooks import Webhook as SvixWebhook

    msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    # UTC aware datetime — sign() 내부 replace(tzinfo=utc)와 epoch 값 일치
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


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client, webhook_secret):
    import base64

    body = json.dumps({"type": "user.created", "data": {"id": "user_x"}}).encode()
    # 올바른 base64 포맷이지만 틀린 서명값 → WebhookVerificationError
    wrong_sig = "v1," + base64.b64encode(b"wrong_signature_value_here").decode()
    bad_headers = {
        "svix-id": "msg_bad",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": wrong_sig,
    }
    res = await client.post("/api/v1/auth/webhook", content=body, headers=bad_headers)
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "webhook_signature_invalid"


@pytest.mark.asyncio
async def test_webhook_user_created_inserts_user(client, db_session, webhook_secret):
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    body = json.dumps(
        {
            "type": "user.created",
            "data": {
                "id": clerk_id,
                "email_addresses": [{"id": "e1", "email_address": "hook@b.com"}],
                "primary_email_address_id": "e1",
                "username": "hooked",
            },
        }
    ).encode()
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json() == {"received": True}

    repo = UserRepository(db_session)
    user = await repo.find_by_clerk_id(clerk_id)
    assert user is not None
    assert user.email == "hook@b.com"
    assert user.username == "hooked"


@pytest.mark.asyncio
async def test_webhook_user_deleted_archives_strategies(client, db_session, webhook_secret):
    from src.auth.models import User

    # 사전: 사용자 + Strategy 2건 생성
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = User(clerk_user_id=clerk_id, email="d@b.com", username="d", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    s1 = Strategy(
        user_id=user.id,
        name="s1",
        pine_source="x",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    s2 = Strategy(
        user_id=user.id,
        name="s2",
        pine_source="x",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    body = json.dumps({"type": "user.deleted", "data": {"id": clerk_id}}).encode()
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200

    from sqlalchemy import select

    # user.id를 expire_all() 전에 캡처 (expire 후 lazy load 방지)
    user_id = user.id
    db_session.expire_all()
    refreshed_user = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    assert refreshed_user.is_active is False

    strategies = (
        await db_session.execute(select(Strategy).where(Strategy.user_id == user_id))
    ).scalars().all()
    assert len(strategies) == 2
    assert all(s.is_archived for s in strategies)


@pytest.mark.asyncio
async def test_webhook_ignores_unknown_event_type(client, webhook_secret):
    body = json.dumps({"type": "session.created", "data": {"id": "sess_1"}}).encode()
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"received": True}

"""Webhook POST endpoint E2E tests (T19).

Tests HMAC acceptance/rejection through the HTTP endpoint.
Webhook is PUBLIC (no JWT) -- HMAC token IS the authentication.
CSO-1: WebhookSecret uses secret_encrypted (bytes, not plaintext).
CSO-6: MAX_WEBHOOK_BODY = 64KB cap verified.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.trading.encryption import EncryptionService
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName, WebhookSecret


@pytest.fixture
def crypto():
    """EncryptionService with a test key for CSO-1 encrypted secrets."""
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


def _sign(secret: str, body_bytes: bytes) -> str:
    """Compute HMAC-SHA256 hex digest (uses plaintext secret, not encrypted)."""
    return hmac_module.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()


def _tv_payload(
    exchange_account_id: str,
    *,
    symbol: str = "BTC/USDT",
    side: str = "buy",
    quantity: str = "0.01",
    order_type: str = "market",
) -> dict:
    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "type": order_type,
        "exchange_account_id": exchange_account_id,
    }


class _FakeDispatcher:
    """Celery dispatcher mock -- prevents Redis connection in tests."""

    def __init__(self) -> None:
        self.dispatched_ids: list[str] = []

    async def dispatch_order_execution(self, order_id):
        self.dispatched_ids.append(str(order_id))


@pytest.mark.asyncio
async def test_webhook_valid_hmac_returns_201(
    client, app, db_session, crypto
):
    """Valid HMAC token -> 201 (order created)."""
    # --- Setup: user, strategy, exchange account, webhook secret ---
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="Webhook Test Strategy",
        pine_source="// test",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test_api_key_1234"),
        api_secret_encrypted=crypto.encrypt("test_api_secret_1234"),
        label="test",
    )
    db_session.add(acct)
    await db_session.flush()

    plaintext_secret = "MY_WEBHOOK_SECRET_123"
    ws = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt(plaintext_secret),
    )
    db_session.add(ws)
    await db_session.flush()

    # --- Override EncryptionService + OrderDispatcher ---
    from src.trading.dependencies import get_encryption_service, get_order_dispatcher

    app.dependency_overrides[get_encryption_service] = lambda: crypto
    app.dependency_overrides[get_order_dispatcher] = _FakeDispatcher

    # --- Build signed request ---
    payload = _tv_payload(str(acct.id))
    body_bytes = json.dumps(payload).encode()
    token = _sign(plaintext_secret, body_bytes)

    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={token}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["strategy_id"] == str(strategy.id)
    assert body["exchange_account_id"] == str(acct.id)
    assert body["symbol"] == "BTC/USDT"
    assert body["side"] == "buy"
    assert body["state"] == "pending"

    # cleanup overrides
    app.dependency_overrides.pop(get_encryption_service, None)
    app.dependency_overrides.pop(get_order_dispatcher, None)


@pytest.mark.asyncio
async def test_webhook_bad_hmac_returns_401(
    client, app, db_session, crypto
):
    """Invalid HMAC token -> 401."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="Webhook Test Strategy",
        pine_source="// test",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test_api_key_1234"),
        api_secret_encrypted=crypto.encrypt("test_api_secret_1234"),
    )
    db_session.add(acct)
    await db_session.flush()

    ws = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt("REAL_SECRET"),
    )
    db_session.add(ws)
    await db_session.flush()

    from src.trading.dependencies import get_encryption_service

    app.dependency_overrides[get_encryption_service] = lambda: crypto

    payload = _tv_payload(str(acct.id))
    body_bytes = json.dumps(payload).encode()
    # Sign with WRONG secret
    token = _sign("WRONG_SECRET", body_bytes)

    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={token}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )

    assert res.status_code == 401, res.text

    app.dependency_overrides.pop(get_encryption_service, None)


@pytest.mark.asyncio
async def test_webhook_missing_token_returns_422(client):
    """Missing token query param -> 422 (FastAPI validation)."""
    strategy_id = uuid4()
    res = await client.post(
        f"/api/v1/webhooks/{strategy_id}",
        content=b'{"symbol":"BTC/USDT","side":"buy","quantity":"0.01"}',
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_webhook_body_too_large_returns_413(client):
    """CSO-6: Content-Length > 64KB -> 413."""
    strategy_id = uuid4()
    # Create a body larger than 64KB
    large_body = b"x" * (64 * 1024 + 1)
    res = await client.post(
        f"/api/v1/webhooks/{strategy_id}?token=fake",
        content=large_body,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(large_body)),
        },
    )
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_webhook_no_auth_header_required(client):
    """Webhook is PUBLIC -- no JWT auth required. Should NOT get 401 for missing auth.

    It should fail for other reasons (missing HMAC match), not for missing JWT.
    """
    strategy_id = uuid4()
    payload = json.dumps({"symbol": "BTC/USDT", "side": "buy", "quantity": "0.01"}).encode()
    token = _sign("some_secret", payload)

    res = await client.post(
        f"/api/v1/webhooks/{strategy_id}?token={token}",
        content=payload,
        headers={"Content-Type": "application/json"},
        # NOTE: no Authorization header -- this is intentional
    )
    # Should be 401 (HMAC mismatch, no secrets in DB) -- NOT 403 (missing JWT)
    assert res.status_code == 401

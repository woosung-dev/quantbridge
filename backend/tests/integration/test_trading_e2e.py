"""End-to-end: webhook POST -> order creation + idempotency.

T21: HTTP-layer integration test.
- Webhook POST with valid HMAC -> 201 + pending order in DB.
- Same Idempotency-Key twice -> same order_id, only 1 order in DB.

Celery dispatch is mocked (NoopDispatcher) -- T16 tests the fill path
separately via _async_execute. The E2E goal is to verify the HTTP layer
integration: DI wiring, HMAC verification, order creation, idempotency.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.dependencies import get_order_dispatcher
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderState,
    WebhookSecret,
)

# EncryptionService aligned with DI factory (same key as get_encryption_service)
_crypto = EncryptionService(settings.trading_encryption_keys)

_WEBHOOK_PLAINTEXT_SECRET = "E2E-SECRET-T21"


def _hmac_sign(secret: str, payload_bytes: bytes) -> str:
    return hmac_module.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


# ── Noop dispatcher: skip Celery, order stays pending ────────────────


class _NoopDispatcher:
    """No Celery dispatch -- order stays in pending state."""

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        pass


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def e2e_user(db_session: AsyncSession):
    from src.auth.models import User

    user = User(
        clerk_user_id="user_e2e_t21",
        email="e2e-t21@test.local",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def e2e_strategy(db_session: AsyncSession, e2e_user):
    s = Strategy(
        user_id=e2e_user.id,
        name="E2E Strategy",
        pine_source="// e2e",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def e2e_exchange_account(db_session: AsyncSession, e2e_user):
    acct = ExchangeAccount(
        user_id=e2e_user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=_crypto.encrypt("e2e-api-key"),
        api_secret_encrypted=_crypto.encrypt("e2e-api-secret"),
        label="E2E Demo",
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


@pytest_asyncio.fixture
async def e2e_webhook_secret(db_session: AsyncSession, e2e_strategy):
    ws = WebhookSecret(
        strategy_id=e2e_strategy.id,
        secret_encrypted=_crypto.encrypt(_WEBHOOK_PLAINTEXT_SECRET),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest_asyncio.fixture
async def e2e_client(app, e2e_webhook_secret) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client with Celery dispatcher overridden to noop."""
    app.dependency_overrides[get_order_dispatcher] = lambda: _NoopDispatcher()
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_order_dispatcher, None)


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_creates_pending_order(
    db_session: AsyncSession,
    e2e_strategy,
    e2e_exchange_account,
    e2e_client: AsyncClient,
):
    """Webhook POST with valid HMAC -> 201 + order in pending state."""
    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "market",
        "quantity": "0.01",
        "exchange_account_id": str(e2e_exchange_account.id),
    }
    body_bytes = json.dumps(payload).encode()
    token = _hmac_sign(_WEBHOOK_PLAINTEXT_SECRET, body_bytes)

    res = await e2e_client.post(
        f"/api/v1/webhooks/{e2e_strategy.id}",
        content=body_bytes,
        headers={"content-type": "application/json"},
        params={"token": token},
    )

    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    body = res.json()
    assert body["state"] == "pending"
    assert body["symbol"] == "BTC/USDT"
    assert body["side"] == "buy"
    assert body["strategy_id"] == str(e2e_strategy.id)
    assert body["exchange_account_id"] == str(e2e_exchange_account.id)

    # Verify order exists in DB
    from src.trading.repository import OrderRepository

    repo = OrderRepository(db_session)
    order = await repo.get_by_id(UUID(body["id"]))
    assert order is not None
    assert order.state == OrderState.pending


@pytest.mark.asyncio
async def test_idempotent_webhook_same_order(
    db_session: AsyncSession,
    e2e_strategy,
    e2e_exchange_account,
    e2e_client: AsyncClient,
):
    """Same Idempotency-Key twice -> same order_id, only 1 order in DB."""
    payload = {
        "symbol": "ETH/USDT",
        "side": "sell",
        "type": "market",
        "quantity": "0.5",
        "exchange_account_id": str(e2e_exchange_account.id),
    }
    body_bytes = json.dumps(payload).encode()
    token = _hmac_sign(_WEBHOOK_PLAINTEXT_SECRET, body_bytes)
    idem_key = "e2e-idempotency-test-key"

    # First request -> 201
    res1 = await e2e_client.post(
        f"/api/v1/webhooks/{e2e_strategy.id}",
        content=body_bytes,
        headers={"content-type": "application/json"},
        params={"token": token, "Idempotency-Key": idem_key},
    )
    assert res1.status_code == 201, f"First: {res1.status_code}: {res1.text}"
    order_id_1 = res1.json()["id"]

    # Second request (same key + same body) -> 200 replay
    res2 = await e2e_client.post(
        f"/api/v1/webhooks/{e2e_strategy.id}",
        content=body_bytes,
        headers={"content-type": "application/json"},
        params={"token": token, "Idempotency-Key": idem_key},
    )
    assert res2.status_code == 200, f"Second: {res2.status_code}: {res2.text}"
    order_id_2 = res2.json()["id"]
    assert res2.headers.get("idempotency-replayed") == "true"

    # Same order
    assert order_id_1 == order_id_2

    # Only 1 order in DB for this idempotency_key
    from src.trading.repository import OrderRepository

    repo = OrderRepository(db_session)
    order = await repo.get_by_idempotency_key(idem_key)
    assert order is not None
    assert str(order.id) == order_id_1

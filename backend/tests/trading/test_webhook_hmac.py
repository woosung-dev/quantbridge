"""WebhookService -- HMAC 검증 (CSO-1: decrypt-then-compare + grace period multi-secret)."""
from __future__ import annotations

import hashlib
import hmac as hmac_module
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.trading.encryption import EncryptionService


@pytest.fixture
def crypto():
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


def _hmac_sign(secret: str, payload_bytes: bytes) -> str:
    return hmac_module.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def test_verify_hmac_accepts_active_secret(db_session, strategy, crypto):
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.webhook import WebhookService

    repo = WebhookSecretRepository(db_session)
    # CSO-1: encrypted storage
    ws = WebhookSecret(strategy_id=strategy.id, secret_encrypted=crypto.encrypt("S1"))
    db_session.add(ws)
    await db_session.flush()

    svc = WebhookService(repo=repo, crypto=crypto, grace_seconds=3600)
    payload = b'{"symbol":"BTC/USDT","side":"buy"}'
    token = _hmac_sign("S1", payload)

    assert await svc.verify(strategy.id, token=token, payload=payload) is True


async def test_verify_hmac_rejects_wrong_signature(db_session, strategy, crypto):
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.webhook import WebhookService

    repo = WebhookSecretRepository(db_session)
    db_session.add(
        WebhookSecret(strategy_id=strategy.id, secret_encrypted=crypto.encrypt("S1"))
    )
    await db_session.flush()

    svc = WebhookService(repo=repo, crypto=crypto, grace_seconds=3600)
    payload = b'{"symbol":"BTC/USDT"}'
    assert await svc.verify(strategy.id, token="bogus-token", payload=payload) is False


async def test_verify_hmac_accepts_recently_revoked_secret_within_grace(
    db_session, strategy, crypto
):
    """rotate 직후 grace window 내에 구 secret도 통과."""
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.webhook import WebhookService

    repo = WebhookSecretRepository(db_session)
    now = datetime.now(UTC)
    old = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt("S_old"),
        revoked_at=now - timedelta(minutes=10),
    )
    new = WebhookSecret(
        strategy_id=strategy.id, secret_encrypted=crypto.encrypt("S_new")
    )
    db_session.add_all([old, new])
    await db_session.flush()

    svc = WebhookService(repo=repo, crypto=crypto, grace_seconds=3600)
    payload = b"{}"

    # 구 secret으로 서명해도 통과 (grace 내)
    assert (
        await svc.verify(
            strategy.id, token=_hmac_sign("S_old", payload), payload=payload
        )
        is True
    )
    # 신 secret도 통과
    assert (
        await svc.verify(
            strategy.id, token=_hmac_sign("S_new", payload), payload=payload
        )
        is True
    )


async def test_verify_hmac_rejects_old_secret_outside_grace(
    db_session, strategy, crypto
):
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.webhook import WebhookService

    repo = WebhookSecretRepository(db_session)
    now = datetime.now(UTC)
    old = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt("S_old"),
        revoked_at=now - timedelta(hours=2),
    )
    db_session.add(old)
    await db_session.flush()

    svc = WebhookService(repo=repo, crypto=crypto, grace_seconds=3600)
    payload = b"{}"
    assert (
        await svc.verify(
            strategy.id, token=_hmac_sign("S_old", payload), payload=payload
        )
        is False
    )


def test_parse_tv_payload_extracts_order_fields():
    from src.trading.webhook import parse_tv_payload

    payload = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": "0.01",
        "type": "market",
    }
    parsed = parse_tv_payload(payload)
    assert parsed.symbol == "BTC/USDT"
    assert parsed.side.value == "buy"
    assert parsed.type.value == "market"
    assert str(parsed.quantity) == "0.01"

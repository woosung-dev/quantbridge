"""WebhookSecretRepository — rotation + grace period 조회 (spec §2.4).

CSO-1: secret_encrypted 바이트만 다룸. Encryption 래핑은 Service 레이어(T11) 담당.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def test_save_and_list_active(db_session, strategy):
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    repo = WebhookSecretRepository(db_session)
    ws = WebhookSecret(strategy_id=strategy.id, secret_encrypted=b"cipher-v1")
    await repo.save(ws)
    await repo.commit()

    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=datetime.now(UTC) - timedelta(hours=1)
    )
    assert len(valid) == 1
    assert valid[0].secret_encrypted == b"cipher-v1"


async def test_rotate_revokes_old_keeps_in_grace(db_session, strategy):
    """기존 secret revoke + grace 내면 list_valid_secrets가 여전히 반환."""
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    repo = WebhookSecretRepository(db_session)

    # v1 생성
    old = WebhookSecret(strategy_id=strategy.id, secret_encrypted=b"cipher-v1")
    await repo.save(old)
    await repo.commit()

    # v1 revoke (현재 시각)
    now = datetime.now(UTC)
    await repo.mark_revoked(old.id, at=now)

    # v2 신규
    new = WebhookSecret(strategy_id=strategy.id, secret_encrypted=b"cipher-v2")
    await repo.save(new)
    await repo.commit()

    # grace 1h 내 → v1 + v2 둘 다 반환
    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=now - timedelta(hours=1)
    )
    secrets = {v.secret_encrypted for v in valid}
    assert secrets == {b"cipher-v1", b"cipher-v2"}


async def test_revoked_outside_grace_is_excluded(db_session, strategy):
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    repo = WebhookSecretRepository(db_session)

    old_revoked_time = datetime.now(UTC) - timedelta(hours=2)
    old = WebhookSecret(
        strategy_id=strategy.id, secret_encrypted=b"cipher-old", revoked_at=old_revoked_time
    )
    await repo.save(old)
    await repo.commit()

    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=datetime.now(UTC) - timedelta(hours=1)
    )
    assert all(v.secret_encrypted != b"cipher-old" for v in valid)


async def test_get_by_id_returns_secret(db_session, strategy):
    """T10 review I1: get_by_id primitive for T11 Service layer."""
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    repo = WebhookSecretRepository(db_session)
    ws = WebhookSecret(strategy_id=strategy.id, secret_encrypted=b"cipher-x")
    saved = await repo.save(ws)
    await repo.commit()

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.secret_encrypted == b"cipher-x"


async def test_get_by_id_miss_returns_none(db_session, strategy):
    from uuid import uuid4

    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    repo = WebhookSecretRepository(db_session)
    assert await repo.get_by_id(uuid4()) is None


async def test_list_valid_secrets_orders_newest_first(db_session, strategy):
    """T10 review S3: newer secrets first (common path optimization for HMAC verify)."""
    from src.trading.models import WebhookSecret
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    repo = WebhookSecretRepository(db_session)

    v1 = WebhookSecret(strategy_id=strategy.id, secret_encrypted=b"cipher-v1")
    await repo.save(v1)
    await repo.commit()

    v2 = WebhookSecret(strategy_id=strategy.id, secret_encrypted=b"cipher-v2")
    await repo.save(v2)
    await repo.commit()

    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=datetime.now(UTC) - timedelta(hours=1)
    )
    assert len(valid) == 2
    assert valid[0].secret_encrypted == b"cipher-v2"
    assert valid[1].secret_encrypted == b"cipher-v1"

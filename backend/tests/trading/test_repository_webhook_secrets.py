"""WebhookSecretRepository — rotation + grace period 조회 (spec §2.4).

CSO-1: secret_encrypted 바이트만 다룸. Encryption 래핑은 Service 레이어(T11) 담당.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def test_save_and_list_active(db_session, strategy):
    from src.trading.models import WebhookSecret
    from src.trading.repository import WebhookSecretRepository

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
    from src.trading.repository import WebhookSecretRepository

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
    from src.trading.repository import WebhookSecretRepository

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

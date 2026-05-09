"""WebhookSecretService — CSO-1 암호화 저장 + rotate grace + issue."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.trading.encryption import EncryptionService


@pytest.fixture
def crypto():
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


async def test_issue_initial_secret(db_session, strategy, crypto):
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.services.webhook_secret_service import WebhookSecretService

    repo = WebhookSecretRepository(db_session)
    svc = WebhookSecretService(repo=repo, crypto=crypto)
    plaintext = await svc.issue(strategy.id)
    await repo.commit()

    assert len(plaintext) >= 32  # 랜덤 토큰, 충분한 엔트로피

    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=datetime.now(UTC)
    )
    assert len(valid) == 1
    # CSO-1: DB에는 암호문만 저장됨 -> 복호화해야 plaintext 일치 확인
    assert crypto.decrypt(valid[0].secret_encrypted) == plaintext


async def test_rotate_revokes_old_and_issues_new(db_session, strategy, crypto):
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.services.webhook_secret_service import WebhookSecretService

    repo = WebhookSecretRepository(db_session)
    svc = WebhookSecretService(repo=repo, crypto=crypto)

    old = await svc.issue(strategy.id)
    await repo.commit()

    new = await svc.rotate(strategy.id, grace_period_seconds=3600)
    await repo.commit()

    assert new != old
    # grace 1h 내: 둘 다 valid
    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=datetime.now(UTC) - timedelta(hours=1)
    )
    # CSO-1: 복호화 후 비교
    decrypted_secrets = {crypto.decrypt(v.secret_encrypted) for v in valid}
    assert old in decrypted_secrets and new in decrypted_secrets


async def test_rotate_with_zero_grace_excludes_old(db_session, strategy, crypto):
    """grace_period=0 -> 즉시 무효."""
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.services.webhook_secret_service import WebhookSecretService

    repo = WebhookSecretRepository(db_session)
    svc = WebhookSecretService(repo=repo, crypto=crypto)

    old = await svc.issue(strategy.id)
    await repo.commit()

    now_before_rotate = datetime.now(UTC)
    await svc.rotate(strategy.id, grace_period_seconds=0)
    await repo.commit()

    # grace_cutoff을 rotation 이후로 설정 -> 구 secret 제외
    valid = await repo.list_valid_secrets(
        strategy.id, grace_cutoff=now_before_rotate + timedelta(milliseconds=1)
    )
    decrypted_secrets = {crypto.decrypt(v.secret_encrypted) for v in valid}
    assert old not in decrypted_secrets

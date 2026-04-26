"""Sprint 13 Phase A.1.1 — Sprint 6 broken bug 회귀 보호.

dogfood Day 1 의 webhook_secrets 0건 root cause:
- WebhookSecretService.issue() / rotate() 가 self._repo.commit() 미호출
- get_async_session() 자동 commit 안 함 → request 종료 시 rollback

이 회귀 테스트는 issue() default commit=True + rotate() 자체 commit 을 강제하여
Sprint 6 broken bug 의 재발을 차단.
"""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import func, select

from src.trading.encryption import EncryptionService
from src.trading.models import WebhookSecret


@pytest.fixture
def crypto() -> EncryptionService:
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


@pytest.mark.asyncio
async def test_issue_default_commits_to_db(db_session, strategy, crypto):
    """A.1.1: issue() default commit=True 가 영구 저장 (Sprint 6 broken bug 회귀)."""
    from src.trading.repository import WebhookSecretRepository
    from src.trading.service import WebhookSecretService

    repo = WebhookSecretRepository(db_session)
    svc = WebhookSecretService(repo=repo, crypto=crypto)
    plaintext = await svc.issue(strategy.id)  # default commit=True
    assert plaintext

    result = await db_session.execute(
        select(func.count())
        .select_from(WebhookSecret)
        .where(WebhookSecret.strategy_id == strategy.id)  # type: ignore[arg-type]
    )
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_issue_commit_false_lets_caller_control(db_session, strategy, crypto):
    """A.1.1: issue(commit=False) — atomic create 흐름. caller 가 마지막 commit."""
    from src.trading.repository import WebhookSecretRepository
    from src.trading.service import WebhookSecretService

    repo = WebhookSecretRepository(db_session)
    svc = WebhookSecretService(repo=repo, crypto=crypto)
    plaintext = await svc.issue(strategy.id, commit=False)
    assert plaintext

    # 동일 session 내 read-your-writes — caller commit 전에도 add+flush 된 row 존재
    result = await db_session.execute(
        select(func.count())
        .select_from(WebhookSecret)
        .where(WebhookSecret.strategy_id == strategy.id)  # type: ignore[arg-type]
    )
    assert result.scalar_one() == 1
    # caller (StrategyService.create) 가 호출하는 commit 시뮬
    await repo.commit()


@pytest.mark.asyncio
async def test_rotate_commits_to_db(db_session, strategy, crypto):
    """A.1.1: rotate() 자체 commit (Sprint 6 broken bug 회귀)."""
    from src.trading.repository import WebhookSecretRepository
    from src.trading.service import WebhookSecretService

    repo = WebhookSecretRepository(db_session)
    svc = WebhookSecretService(repo=repo, crypto=crypto)

    # initial issue
    await svc.issue(strategy.id)
    # rotate
    new_plaintext = await svc.rotate(strategy.id, grace_period_seconds=300)
    assert new_plaintext

    # row count: 1 active + 1 revoked = 2
    result = await db_session.execute(
        select(func.count())
        .select_from(WebhookSecret)
        .where(WebhookSecret.strategy_id == strategy.id)  # type: ignore[arg-type]
    )
    assert result.scalar_one() == 2

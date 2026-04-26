"""Sprint 13 Phase A.1.1 — Sprint 6 broken bug 회귀 보호.

dogfood Day 1 의 webhook_secrets 0건 root cause:
- WebhookSecretService.issue() / rotate() 가 self._repo.commit() 미호출
- get_async_session() 자동 commit 안 함 → request 종료 시 rollback

이 회귀 테스트는 issue() default commit=True + rotate() 자체 commit 을 강제하여
Sprint 6 broken bug 의 재발을 차단.

G.2 codex challenge P2 #1 보강: db_session 기반 테스트는 same-session
read-your-writes 로 인해 commit() 누락도 통과 가능. AsyncMock spy 로 repo.commit()
호출 자체를 직접 검증 (Sprint 6 broken bug 가 commit 누락이라 commit 호출 검증이
가장 정확한 회귀 테스트).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

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


# ── Mock spy 회귀 (G.2 challenge P2 #1 보강) — repo.commit() 호출 자체 검증 ──
# db_session 기반 테스트는 same-session read-your-writes 로 commit() 누락도 통과
# 가능. mock spy 가 Sprint 6 broken bug 의 본질 (commit 호출 누락) 을 직접 검증.


@pytest.mark.asyncio
async def test_issue_default_calls_repo_commit():
    """A.1.1 spy: issue() default commit=True 가 repo.commit() 호출 강제."""
    from src.trading.service import WebhookSecretService

    repo = AsyncMock()
    crypto_mock = MagicMock()
    crypto_mock.encrypt.return_value = b"encrypted_bytes"
    svc = WebhookSecretService(repo=repo, crypto=crypto_mock)

    plaintext = await svc.issue(uuid4())
    assert plaintext

    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← Sprint 6 broken bug 핵심


@pytest.mark.asyncio
async def test_issue_commit_false_does_not_call_commit():
    """A.1.1 spy: issue(commit=False) — atomic create 흐름. repo.commit() 호출 X."""
    from src.trading.service import WebhookSecretService

    repo = AsyncMock()
    crypto_mock = MagicMock()
    crypto_mock.encrypt.return_value = b"encrypted_bytes"
    svc = WebhookSecretService(repo=repo, crypto=crypto_mock)

    plaintext = await svc.issue(uuid4(), commit=False)
    assert plaintext

    repo.save.assert_awaited_once()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_rotate_calls_repo_commit():
    """A.1.1 spy: rotate() 가 repo.commit() 호출 강제 (Sprint 6 broken bug 핵심)."""
    from src.trading.service import WebhookSecretService

    repo = AsyncMock()
    crypto_mock = MagicMock()
    crypto_mock.encrypt.return_value = b"encrypted_bytes"
    svc = WebhookSecretService(repo=repo, crypto=crypto_mock)

    plaintext = await svc.rotate(uuid4(), grace_period_seconds=300)
    assert plaintext

    repo.revoke_all_active.assert_awaited_once()
    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← Sprint 6 broken bug 핵심


# ── Mock spy 회귀: OrderService outer commit (Sprint 13 dogfood Day 2 hotfix) ──
# OrderService._execute_inner 가 begin_nested context exit 후 outer commit 호출하지
# 않으면 session.close() 시 ROLLBACK 으로 INSERT 영구 저장 안 됨. dogfood Day 2
# 첫 webhook 호출에서 발견된 broken bug. Sprint 6 webhook_secret 과 동일 패턴.


@pytest.mark.asyncio
async def test_order_service_execute_calls_outer_commit():
    """Sprint 13 dogfood Day 2 hotfix: OrderService.execute 가 outer commit 호출 강제."""
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.trading.models import Order, OrderSide, OrderState, OrderType
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    session = AsyncMock(spec=AsyncSession)
    # begin_nested 가 async context manager 지원 — __aenter__/__aexit__ 자체 동작
    session.begin_nested = MagicMock(return_value=AsyncMock())

    repo = AsyncMock()
    saved_order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
        idempotency_key=None,
        idempotency_payload_hash=None,
        leverage=None,
        margin_mode=None,
    )
    repo.save = AsyncMock(return_value=saved_order)
    repo.get_by_id = AsyncMock(return_value=saved_order)

    kill_switch = AsyncMock()
    kill_switch.ensure_not_gated = AsyncMock()

    dispatcher = AsyncMock()

    svc = OrderService(
        session=session,
        repo=repo,
        dispatcher=dispatcher,
        kill_switch=kill_switch,
        sessions_port=None,
        exchange_service=None,
    )

    req = OrderRequest(
        strategy_id=saved_order.strategy_id,
        exchange_account_id=saved_order.exchange_account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    await svc.execute(req, idempotency_key=None, body_hash=None)

    # 핵심 검증 — outer commit 호출 강제 (Sprint 6 broken bug 와 동일 패턴)
    session.commit.assert_awaited_once()

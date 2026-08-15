"""탈퇴가 **돈을 멈춘다** (2026-08-15 surface-truth · S3).

**실사고 모양** — 종전 `user.deleted` 분기는 `set_inactive` + 전략 archive 뿐이었다.
그래서 탈퇴하면 **UI 만 잠겼다**:

- `live_signal_session_repository.list_active_due` 는 `WHERE is_active = true` 만 보고
  `users` 를 조인하지 않는다 ⇒ beat 가 그 사람의 세션을 계속 평가해 저장된 거래소 키를
  복호화하고 **실주문을 냈다**.
- `webhook.py` 의 HMAC 검증은 strategy 만 증명한다 ⇒ 유출된 TradingView 웹훅 시크릿이
  탈퇴 후에도 계속 체결됐다. 그 웹훅 라우트는 공개다(`trading/router.py`).
- `order_service.py` 에 `is_active` 는 **한 번도 등장하지 않았다**.

★**이 파일은 순수 함수가 아니라 배선을 잰다** — 실제 `db_session` 에 두 사용자를 심고
`UserService.handle_clerk_event` 를 그대로 태운다. 「소유자만」 닫히는지(음성 대조)와
「`ExchangeAccount` 행은 안 지운다」(확정된 사용자 결정)도 같은 자리에서 고정한다.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.service import UserService
from src.core.config import settings as app_settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    WebhookSecret,
)

_PLAINTEXT_SECRET = "tv-webhook-secret-value"


async def _seed_tenant(
    db_session: AsyncSession, *, tag: str, crypto: EncryptionService
) -> tuple[User, Strategy, LiveSignalSession, WebhookSecret]:
    user = User(clerk_user_id=f"{tag}-{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@test.local")
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name=f"{tag} strategy",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    live = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
    )
    secret = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt(_PLAINTEXT_SECRET),
    )
    db_session.add_all([live, secret])
    await db_session.flush()
    return user, strategy, live, secret


def _service(db_session: AsyncSession) -> UserService:
    """production DI(`auth/dependencies.get_user_service`) 와 **같은 조립**을 재현한다."""
    from src.auth.repository import UserRepository
    from src.strategy.repository import StrategyRepository
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    return UserService(
        user_repo=UserRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        live_session_repo=LiveSignalSessionRepository(db_session),
        webhook_secret_repo=WebhookSecretRepository(db_session),
    )


@pytest.fixture
def crypto() -> EncryptionService:
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


@pytest.mark.asyncio
async def test_user_deleted_stops_sessions_and_revokes_webhook_secrets(
    db_session: AsyncSession, crypto: EncryptionService
) -> None:
    """★양성 — 탈퇴자의 세션은 내려가고 시크릿은 즉시 폐기된다."""
    gone, _gone_strategy, gone_session, gone_secret = await _seed_tenant(
        db_session, tag="gone", crypto=crypto
    )
    await _service(db_session).handle_clerk_event(
        {"type": "user.deleted", "data": {"id": gone.clerk_user_id}}
    )

    await db_session.refresh(gone_session)
    await db_session.refresh(gone_secret)

    assert gone_session.is_active is False, "탈퇴자의 활성 세션이 남아 있으면 beat 가 계속 발주한다"
    assert gone_session.deactivated_reason == "account_deleted", (
        f"사유가 정본 값이어야 한다 (실제 {gone_session.deactivated_reason!r})"
    )
    assert gone_session.deactivated_at is not None

    assert gone_secret.revoked_at is not None, "탈퇴 후에도 웹훅 시크릿이 살아 있다"
    # ★grace 0 — `list_valid_secrets` 는 `revoked_at > now - grace` 를 아직 유효로 센다.
    #   revoke 시각이 그 창 **밖**(과거)이어야 다음 웹훅부터 즉시 거부된다.
    grace_cutoff = datetime.now(UTC) - timedelta(seconds=app_settings.webhook_secret_grace_seconds)
    assert gone_secret.revoked_at <= grace_cutoff, (
        "revoke 시각이 grace 창 안이면 최대 1시간 동안 유출 시크릿이 계속 체결된다 "
        f"(revoked_at={gone_secret.revoked_at} > cutoff={grace_cutoff})"
    )


@pytest.mark.asyncio
async def test_user_deleted_leaves_other_tenants_alone(
    db_session: AsyncSession, crypto: EncryptionService
) -> None:
    """★음성 대조 — 이게 없으면 「전부 내리기」로도 위 테스트가 통과한다(판별력 0)."""
    gone, _gs, _gsess, _gsec = await _seed_tenant(db_session, tag="gone", crypto=crypto)
    _stay, _ss, stay_session, stay_secret = await _seed_tenant(
        db_session, tag="stay", crypto=crypto
    )

    await _service(db_session).handle_clerk_event(
        {"type": "user.deleted", "data": {"id": gone.clerk_user_id}}
    )

    await db_session.refresh(stay_session)
    await db_session.refresh(stay_secret)
    assert stay_session.is_active is True, "남의 세션을 내렸다"
    assert stay_session.deactivated_reason is None
    assert stay_secret.revoked_at is None, "남의 웹훅 시크릿을 폐기했다"


@pytest.mark.asyncio
async def test_user_deleted_does_not_delete_exchange_account_rows(
    db_session: AsyncSession, crypto: EncryptionService
) -> None:
    """범위 고정 — `exchange_accounts` **행 삭제는 하지 않는다**.

    2026-08-11 사용자 결정(「삭제하지 않는다 — 비활성 + 409」)이고 FK `ondelete=RESTRICT`
    3곳이 그것을 원장에서 강제한다. credential 파기 정책은 별도 결정 사항이다([BL-477]·
    [BL-529]·[BL-592]). 이 테스트는 그 경계가 조용히 넓어지는 것을 막는다.
    """
    gone, _s, _sess, _sec = await _seed_tenant(db_session, tag="gone", crypto=crypto)
    before = (
        (
            await db_session.execute(
                select(ExchangeAccount).where(ExchangeAccount.user_id == gone.id)  # type: ignore[arg-type]
            )
        )
        .scalars()
        .all()
    )
    assert before, "픽스처 전제 — 계정 행이 있어야 한다"

    await _service(db_session).handle_clerk_event(
        {"type": "user.deleted", "data": {"id": gone.clerk_user_id}}
    )

    after = (
        (
            await db_session.execute(
                select(ExchangeAccount).where(ExchangeAccount.user_id == gone.id)  # type: ignore[arg-type]
            )
        )
        .scalars()
        .all()
    )
    assert len(after) == len(before), "이번 회차는 계정 행을 지우지 않는다 (사용자 결정)"


@pytest.mark.asyncio
async def test_webhook_verify_rejects_after_owner_deleted(
    db_session: AsyncSession, crypto: EncryptionService
) -> None:
    """★배선 — 시크릿 revoke 가 **실제 웹훅 검증 경로**에서 거부로 나타난다.

    `revoked_at` 컬럼을 확인하는 것만으로는 부족하다 — `WebhookService.verify` 가
    grace 창 안의 시크릿을 아직 유효로 세기 때문이다. 그 함수까지 태워야 증거가 된다.
    """
    from src.trading.webhook import WebhookService

    gone, strategy, _sess, _sec = await _seed_tenant(db_session, tag="gone", crypto=crypto)
    payload = b'{"action":"buy"}'
    token = hmac.new(_PLAINTEXT_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    from src.strategy.repository import StrategyRepository
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    svc = WebhookService(
        repo=WebhookSecretRepository(db_session),
        crypto=crypto,
        grace_seconds=app_settings.webhook_secret_grace_seconds,
        strategy_repo=StrategyRepository(db_session),
    )
    assert await svc.verify(strategy.id, token=token, payload=payload) is True, (
        "픽스처 전제 — 탈퇴 전에는 통과해야 한다(음성 대조)"
    )

    await _service(db_session).handle_clerk_event(
        {"type": "user.deleted", "data": {"id": gone.clerk_user_id}}
    )

    assert await svc.verify(strategy.id, token=token, payload=payload) is False, (
        "탈퇴 후에도 유출 웹훅 시크릿이 체결된다"
    )


@pytest.mark.asyncio
async def test_owner_inactive_gate_blocks_orders(db_session: AsyncSession) -> None:
    """★심층 방어 — `_StrategySessionsAdapter.is_owner_active` 가 탈퇴자를 False 로 낸다.

    원천 차단(세션·시크릿)이 한 박자 늦는 자리(큐에 이미 들어간 tick·수기 주문)에서
    `OrderService` 가 마지막으로 묻는 술어다. 모르는 user_id 는 **fail-closed** 다.
    """
    from src.trading.dependencies import _StrategySessionsAdapter

    adapter = _StrategySessionsAdapter(db_session)
    alive = User(clerk_user_id=f"alive-{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@t.local")
    db_session.add(alive)
    await db_session.flush()

    assert await adapter.is_owner_active(alive.id) is True
    alive.is_active = False
    await db_session.flush()
    assert await adapter.is_owner_active(alive.id) is False
    assert await adapter.is_owner_active(UUID(int=0)) is False, "모르는 소유자는 fail-closed"


@pytest.mark.asyncio
async def test_queued_orders_are_blocked_at_dispatch_after_deletion(
    db_session: AsyncSession, crypto: EncryptionService
) -> None:
    """★2026-08-15 적대 리뷰 P1 — **이미 큐에 있던 주문**은 발주 직전에 막힌다.

    `OrderService.execute` 의 게이트는 **주문을 만드는 시점**을 잰다. 그런데 주문은
    `pending` 으로 원장에 앉았다가 Celery 워커가 나중에 집어 거래소로 보낸다. 탈퇴 처리는
    세션과 웹훅 시크릿만 닫고 `pending` 주문은 건드리지 않으므로, 그 사이에 탈퇴가
    일어나면 **그 주문은 그대로 거래소로 나갔다**.

    ⇒ `OrderRepository.strategy_owner_is_active` 가 워커의 마지막 문이다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    gone, gone_strategy, _sess, _sec = await _seed_tenant(db_session, tag="gone", crypto=crypto)
    repo = OrderRepository(db_session)

    assert await repo.strategy_owner_is_active(gone_strategy.id) is True, (
        "픽스처 전제 — 탈퇴 전에는 통과해야 한다(음성 대조)"
    )

    await _service(db_session).handle_clerk_event(
        {"type": "user.deleted", "data": {"id": gone.clerk_user_id}}
    )

    assert await repo.strategy_owner_is_active(gone_strategy.id) is False, (
        "탈퇴 후에도 큐에 있던 주문이 거래소로 나간다"
    )
    assert await repo.strategy_owner_is_active(UUID(int=0)) is False, (
        "모르는 전략은 fail-closed — 프로덕션에서는 FK 가 행의 존재를 보장한다"
    )

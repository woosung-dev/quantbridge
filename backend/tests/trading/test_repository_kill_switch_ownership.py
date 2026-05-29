"""KillSwitchEventRepository — tenant scoping (CF1 IDOR fix).

list/resolve 는 호출자 소유(strategy 또는 exchange_account 의 user_id)인 이벤트만
보거나 변경할 수 있어야 한다. KillSwitchEvent 에는 user_id 컬럼이 없으므로
strategy_id->Strategy.user_id 또는 exchange_account_id->ExchangeAccount.user_id JOIN 으로 소유 판정.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    KillSwitchEvent,
    KillSwitchTriggerType,
)
from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository


async def _account(db_session: AsyncSession, owner: User) -> ExchangeAccount:
    acct = ExchangeAccount(
        user_id=owner.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


async def _other_user(db_session: AsyncSession) -> User:
    u = User(clerk_user_id=f"clerk_{uuid4().hex[:8]}", email="other@example.com")
    db_session.add(u)
    await db_session.flush()
    return u


async def test_list_recent_by_user_excludes_other_tenants(
    db_session: AsyncSession, user: User, strategy
):
    """user A 의 cumulative_loss event 와 user B 의 daily_loss event 분리 노출."""
    repo = KillSwitchEventRepository(db_session)
    user_b = await _other_user(db_session)
    acct_b = await _account(db_session, user_b)

    # A 소유: cumulative_loss (strategy=A)
    ev_a = await repo.save(
        KillSwitchEvent(
            trigger_type=KillSwitchTriggerType.cumulative_loss,
            strategy_id=strategy.id,
            trigger_value=Decimal("15"),
            threshold=Decimal("10"),
        )
    )
    # B 소유: daily_loss (account=B)
    ev_b = await repo.save(
        KillSwitchEvent(
            trigger_type=KillSwitchTriggerType.daily_loss,
            exchange_account_id=acct_b.id,
            trigger_value=Decimal("600"),
            threshold=Decimal("500"),
        )
    )
    await repo.commit()

    a_events = await repo.list_recent_by_user(user_id=user.id, limit=50, offset=0)
    a_ids = {e.id for e in a_events}
    assert ev_a.id in a_ids
    assert ev_b.id not in a_ids, "user A 가 user B 의 kill-switch event 를 볼 수 있음 (IDOR)"

    b_events = await repo.list_recent_by_user(user_id=user_b.id, limit=50, offset=0)
    b_ids = {e.id for e in b_events}
    assert ev_b.id in b_ids
    assert ev_a.id not in b_ids


async def test_get_owned_rejects_cross_tenant(
    db_session: AsyncSession, user: User, strategy
):
    """get_owned(event, 다른 user) → None (resolve 권한 차단)."""
    repo = KillSwitchEventRepository(db_session)
    user_b = await _other_user(db_session)

    ev_a = await repo.save(
        KillSwitchEvent(
            trigger_type=KillSwitchTriggerType.cumulative_loss,
            strategy_id=strategy.id,
            trigger_value=Decimal("15"),
            threshold=Decimal("10"),
        )
    )
    await repo.commit()

    assert await repo.get_owned(ev_a.id, user_id=user_b.id) is None
    owned = await repo.get_owned(ev_a.id, user_id=user.id)
    assert owned is not None and owned.id == ev_a.id

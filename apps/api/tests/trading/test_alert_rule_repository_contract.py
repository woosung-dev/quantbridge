"""AlertRuleRepository의 SQL 필터와 트랜잭션 계약을 실 DB로 고정한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import Strategy
from src.trading.models import (
    AlertChannel,
    AlertRule,
    AlertRuleType,
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
)
from src.trading.repositories.alert_rule_repository import AlertRuleRepository

_CREATED_AT = datetime(2026, 8, 21, 9, tzinfo=UTC)


async def _seed_account(db_session: AsyncSession, user: User) -> ExchangeAccount:
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _seed_session(
    db_session: AsyncSession,
    *,
    user: User,
    strategy: Strategy,
    account: ExchangeAccount,
    symbol: str = "BTCUSDT",
) -> LiveSignalSession:
    live_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=symbol,
        interval=LiveSignalInterval.m5,
    )
    db_session.add(live_session)
    await db_session.flush()
    return live_session


async def _seed_rule(
    db_session: AsyncSession,
    *,
    session_id: UUID,
    rule_type: AlertRuleType,
    is_active: bool = True,
    created_at: datetime | None = None,
) -> AlertRule:
    rule = AlertRule(
        session_id=session_id,
        rule_type=rule_type,
        threshold_percent=Decimal("10") if rule_type == AlertRuleType.loss_limit else None,
        channel=AlertChannel.slack,
        is_active=is_active,
        created_at=created_at or _CREATED_AT,
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


@pytest.mark.asyncio
async def test_create_flushes_and_is_queryable_without_commit(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    rule = AlertRule(
        session_id=live_session.id,
        rule_type=AlertRuleType.loss_limit,
        threshold_percent=Decimal("10"),
        channel=AlertChannel.slack,
    )
    repo = AlertRuleRepository(db_session)

    saved = await repo.create(rule)

    assert saved is rule
    assert saved.id is not None
    assert await repo.get_active_by_id(saved.id) is saved


@pytest.mark.asyncio
async def test_get_active_by_id_excludes_inactive_rule(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    active = await _seed_rule(
        db_session, session_id=live_session.id, rule_type=AlertRuleType.watchdog
    )
    inactive = await _seed_rule(
        db_session,
        session_id=live_session.id,
        rule_type=AlertRuleType.loss_limit,
        is_active=False,
    )
    repo = AlertRuleRepository(db_session)

    assert await repo.get_active_by_id(active.id) is active
    assert await repo.get_active_by_id(inactive.id) is None


@pytest.mark.asyncio
async def test_deactivate_returns_one_and_hides_rule(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    rule = await _seed_rule(
        db_session, session_id=live_session.id, rule_type=AlertRuleType.loss_limit
    )
    repo = AlertRuleRepository(db_session)

    assert await repo.deactivate(rule.id) == 1
    assert rule.is_active is False
    assert await repo.get_active_by_id(rule.id) is None


@pytest.mark.asyncio
async def test_deactivate_already_inactive_rule_returns_zero(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    rule = await _seed_rule(
        db_session,
        session_id=live_session.id,
        rule_type=AlertRuleType.watchdog,
        is_active=False,
    )

    assert await AlertRuleRepository(db_session).deactivate(rule.id) == 0


@pytest.mark.asyncio
async def test_deactivate_unknown_rule_returns_zero(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    await _seed_session(db_session, user=user, strategy=strategy, account=account)

    assert await AlertRuleRepository(db_session).deactivate(uuid4()) == 0


@pytest.mark.asyncio
async def test_find_active_watchdog_rules_applies_all_three_filters(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    target_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    active_watchdog = await _seed_rule(
        db_session, session_id=target_session.id, rule_type=AlertRuleType.watchdog
    )
    await _seed_rule(
        db_session,
        session_id=target_session.id,
        rule_type=AlertRuleType.watchdog,
        is_active=False,
    )
    await _seed_rule(db_session, session_id=target_session.id, rule_type=AlertRuleType.loss_limit)
    other_session = await _seed_session(
        db_session, user=user, strategy=strategy, account=account, symbol="ETHUSDT"
    )
    await _seed_rule(db_session, session_id=other_session.id, rule_type=AlertRuleType.watchdog)

    found = await AlertRuleRepository(db_session).find_active_watchdog_rules_for(target_session.id)

    assert [rule.id for rule in found] == [active_watchdog.id]


@pytest.mark.asyncio
async def test_list_by_session_returns_active_rules_newest_first(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    earlier = await _seed_rule(
        db_session,
        session_id=live_session.id,
        rule_type=AlertRuleType.loss_limit,
        created_at=_CREATED_AT,
    )
    later = await _seed_rule(
        db_session,
        session_id=live_session.id,
        rule_type=AlertRuleType.watchdog,
        created_at=_CREATED_AT + timedelta(minutes=1),
    )
    await _seed_rule(
        db_session,
        session_id=live_session.id,
        rule_type=AlertRuleType.loss_limit,
        is_active=False,
        created_at=_CREATED_AT + timedelta(minutes=2),
    )

    found = await AlertRuleRepository(db_session).list_by_session(live_session.id)

    assert [rule.id for rule in found] == [later.id, earlier.id]


@pytest.mark.asyncio
async def test_commit_and_rollback_control_rule_visibility(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(db_session, user=user, strategy=strategy, account=account)
    session_id = live_session.id
    repo = AlertRuleRepository(db_session)
    await repo.commit()

    rolled_back = AlertRule(
        session_id=session_id,
        rule_type=AlertRuleType.watchdog,
        channel=AlertChannel.slack,
    )
    await repo.create(rolled_back)
    await repo.rollback()

    assert await repo.get_active_by_id(rolled_back.id) is None

    committed = AlertRule(
        session_id=session_id,
        rule_type=AlertRuleType.loss_limit,
        threshold_percent=Decimal("10"),
        channel=AlertChannel.slack,
    )
    await repo.create(committed)
    await repo.commit()

    assert await repo.get_active_by_id(committed.id) is committed

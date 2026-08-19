"""[BL-762] 주문·라이브 세션 소유권 getter의 DB 질의 경계를 검증한다."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository


async def _create_other_user(db_session: AsyncSession) -> User:
    other_user = User(
        auth_subject=f"ownership-getter-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
    )
    db_session.add(other_user)
    await db_session.flush()
    return other_user


async def _create_account(db_session: AsyncSession, owner: User) -> ExchangeAccount:
    account = ExchangeAccount(
        user_id=owner.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _create_strategy(db_session: AsyncSession, owner: User) -> Strategy:
    strategy = Strategy(
        user_id=owner.id,
        name=f"ownership-getter-{uuid4().hex}",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    return strategy


async def _create_order(db_session: AsyncSession, owner: User, strategy: Strategy) -> Order:
    account = await _create_account(db_session, owner)
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.pending,
    )
    db_session.add(order)
    await db_session.flush()
    return order


async def _create_live_session(
    db_session: AsyncSession, owner: User, strategy: Strategy
) -> LiveSignalSession:
    account = await _create_account(db_session, owner)
    session = LiveSignalSession(
        user_id=owner.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add(session)
    await db_session.flush()
    return session


@pytest.mark.asyncio
async def test_order_get_by_id_for_user_returns_owned_order(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    repo = OrderRepository(db_session)
    order = await _create_order(db_session, user, strategy)

    result = await repo.get_by_id_for_user(order.id, user.id)

    assert result is not None
    assert result.id == order.id


@pytest.mark.asyncio
async def test_order_get_by_id_for_user_rejects_other_users_order(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    repo = OrderRepository(db_session)
    other_user = await _create_other_user(db_session)
    other_strategy = await _create_strategy(db_session, other_user)
    order = await _create_order(db_session, other_user, other_strategy)

    assert await repo.get_by_id_for_user(order.id, user.id) is None


@pytest.mark.asyncio
async def test_order_get_by_id_for_user_returns_none_for_missing_id(
    db_session: AsyncSession, user: User
) -> None:
    repo = OrderRepository(db_session)

    assert await repo.get_by_id_for_user(uuid4(), user.id) is None


@pytest.mark.asyncio
async def test_live_session_get_by_id_for_user_returns_owned_session(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    repo = LiveSignalSessionRepository(db_session)
    session = await _create_live_session(db_session, user, strategy)

    result = await repo.get_by_id_for_user(session.id, user.id)

    assert result is not None
    assert result.id == session.id


@pytest.mark.asyncio
async def test_live_session_get_by_id_for_user_rejects_other_users_session(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    repo = LiveSignalSessionRepository(db_session)
    other_user = await _create_other_user(db_session)
    other_strategy = await _create_strategy(db_session, other_user)
    session = await _create_live_session(db_session, other_user, other_strategy)

    assert await repo.get_by_id_for_user(session.id, user.id) is None


@pytest.mark.asyncio
async def test_live_session_get_by_id_for_user_returns_none_for_missing_id(
    db_session: AsyncSession, user: User
) -> None:
    repo = LiveSignalSessionRepository(db_session)

    assert await repo.get_by_id_for_user(UUID(int=0), user.id) is None

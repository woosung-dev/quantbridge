"""슬롯 DB의 실제 UID·심볼 소유권 조회와 트랜잭션 경합을 검증한다."""

import asyncio
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.auth.models import User
from src.strategy.models import ParseStatus, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveRiskState,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository


@pytest.fixture
async def scope(db_session, user):
    async def account(uid=None, *, mode=ExchangeMode.demo):
        value = ExchangeAccount(
            user_id=user.id,
            exchange=ExchangeName.bybit,
            mode=mode,
            exchange_uid=uid,
            api_key_encrypted=b"fake",
            api_secret_encrypted=b"fake",
        )
        db_session.add(value)
        await db_session.flush()
        return value

    async def live(account, *, code=True, active=True, symbol="BTC/USDT"):
        strategy = Strategy(
            user_id=user.id,
            name="ownership fixture",
            pine_source="// fixture",
            parse_status=ParseStatus.ok,
        )
        db_session.add(strategy)
        await db_session.flush()
        value = LiveSignalSession(
            user_id=user.id,
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol=symbol,
            interval="1h",
            is_active=active,
            execution_snapshot={"source_policy": "code_v1"} if code else None,
        )
        db_session.add(value)
        await db_session.flush()
        return value

    async def entry(live, *, symbol=None, reduce_only=False):
        value = Order(
            strategy_id=live.strategy_id,
            exchange_account_id=live.exchange_account_id,
            symbol=symbol or live.symbol,
            side=OrderSide.buy,
            type=OrderType.market,
            state=OrderState.submitted,
            quantity=D(2),
            reduce_only=reduce_only,
        )
        db_session.add(value)
        await db_session.flush()
        return value

    return account, live, entry


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing,incoming,allowed",
    [(True, True, False), (True, False, False), (False, True, False), (False, False, True)],
)
async def test_active_sessions_are_exclusive_when_either_side_is_code(
    db_session, scope, existing, incoming, allowed
):
    account, live, _ = scope
    account = await account()
    await live(account, code=existing)
    assert (
        await LiveSignalSessionRepository(db_session).acquire_code_symbol_admission(
            account.id, "BTCUSDT", is_code=incoming
        )
        is allowed
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "left_uid,right_uid,same_scope",
    [("123", " \t123\n", True), (None, None, False), ("", " \t\n", False), ("123", "124", False)],
)
async def test_known_uid_siblings_share_ownership_but_unknowns_do_not(
    db_session, scope, left_uid, right_uid, same_scope
):
    account, live, _ = scope
    first, second = await account(left_uid), await account(right_uid)
    await live(first)
    assert (
        await LiveSignalSessionRepository(db_session).acquire_code_symbol_admission(
            second.id, "BTC/USDT:USDT", is_code=True
        )
        is not same_scope
    )


@pytest.mark.asyncio
async def test_different_symbol_and_mode_do_not_collide(db_session, scope):
    account, live, _ = scope
    first = await account("123")
    await live(first)
    other_mode = await account("123", mode=ExchangeMode.live)
    repo = LiveSignalSessionRepository(db_session)
    assert await repo.acquire_code_symbol_admission(first.id, "ETHUSDT", is_code=True)
    assert await repo.acquire_code_symbol_admission(other_mode.id, "BTCUSDT", is_code=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("unfinished", ["position", "entry", "cleanup", "marker", None])
async def test_inactive_code_owner_retained_until_all_cleanup_is_confirmed(
    db_session, scope, unfinished
):
    account, live, entry = scope
    account = await account()
    old = await live(account, active=False)
    order = await entry(old)
    order.state = OrderState.filled
    state = LiveRiskState(
        session_id=old.id,
        direction="long",
        entry_order_id=order.id,
        expected_quantity=D(2),
        reference_bars=[],
        qty_step=D("0.1"),
        min_qty=D("0.1"),
        provisional_stop=D(90),
        entry_terminal=unfinished != "entry",
        cancels_confirmed=unfinished != "cleanup",
        position_quantity=D(1) if unfinished == "position" else D(0),
        unsettled_exit_quantity=D(1) if unfinished == "marker" else D(0),
    )
    db_session.add(state)
    await db_session.flush()
    repo = LiveSignalSessionRepository(db_session)
    for incoming in (True, False):
        assert await repo.acquire_code_symbol_admission(
            account.id, "BTCUSDT", is_code=incoming
        ) is (unfinished is None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "symbol,reduce_only,allowed",
    [("BTC/USDT", False, False), ("ETH/USDT", False, True), ("BTC/USDT", True, True)],
)
async def test_inactive_legacy_resting_entry_reserves_symbol(
    db_session, scope, symbol, reduce_only, allowed
):
    account, live, entry = scope
    account = await account()
    old = await live(account, code=False, active=False)
    await entry(old, symbol=symbol, reduce_only=reduce_only)
    repo = LiveSignalSessionRepository(db_session)
    assert await repo.acquire_code_symbol_admission(account.id, "BTCUSDT", is_code=True) is allowed
    assert await repo.acquire_code_symbol_admission(account.id, "BTCUSDT", is_code=False)


@pytest.mark.asyncio
async def test_entry_recheck_requires_active_owner_and_exempts_only_its_current_entry(
    db_session, scope
):
    account, live, entry = scope
    account = await account()
    owner = await live(account)
    order = await entry(owner)
    order.risk_context = {"session_id": str(owner.id), "role": "entry", "generation": 1}
    risk = LiveRiskState(
        session_id=owner.id,
        direction="long",
        entry_order_id=order.id,
        expected_quantity=D(2),
        reference_bars=[],
        qty_step=D("0.1"),
        min_qty=D("0.1"),
        provisional_stop=D(90),
    )
    db_session.add(risk)
    await db_session.flush()
    repo = CodeRiskRepository(db_session)
    assert await repo.acquire_entry_admission(owner.id)
    order.risk_context = {"session_id": str(owner.id), "role": "entry", "generation": 2}
    await db_session.flush()
    assert not await repo.acquire_entry_admission(owner.id)
    order.risk_context = {"session_id": str(uuid4()), "role": "entry", "generation": 1}
    await db_session.flush()
    assert not await repo.acquire_entry_admission(owner.id)
    order.risk_context = {"session_id": str(owner.id), "role": "entry", "generation": 1}
    owner.is_active = False
    await db_session.flush()
    assert not await repo.acquire_entry_admission(owner.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["active", "inactive_risk", "inactive_order"])
async def test_registration_lock_serializes_two_strategies_on_uid_sibling_accounts(
    _test_engine, phase
):
    """독립 두 connection: 첫 INSERT commit 전 두 번째는 대기하고 이후 거부된다."""
    maker = async_sessionmaker(_test_engine, expire_on_commit=False)
    user_id, account_ids, strategy_ids = uuid4(), [uuid4(), uuid4()], [uuid4(), uuid4()]
    async with maker() as setup:
        setup.add(User(id=user_id, auth_subject=f"scope-{user_id}", email=f"{user_id}@test.local"))
        await setup.flush()
        setup.add_all(
            [
                ExchangeAccount(
                    id=identifier,
                    user_id=user_id,
                    exchange=ExchangeName.bybit,
                    mode=ExchangeMode.demo,
                    exchange_uid="same-uid",
                    api_key_encrypted=b"fake",
                    api_secret_encrypted=b"fake",
                )
                for identifier in account_ids
            ]
            + [
                Strategy(
                    id=identifier,
                    user_id=user_id,
                    name="ownership race",
                    pine_source="// fixture",
                    parse_status=ParseStatus.ok,
                )
                for identifier in strategy_ids
            ]
        )
        await setup.commit()
    acquired, release = asyncio.Event(), asyncio.Event()

    async def register(index):
        async with maker() as session:
            allowed = await LiveSignalSessionRepository(session).acquire_code_symbol_admission(
                account_ids[index], "BTCUSDT", is_code=True
            )
            if allowed:
                live = LiveSignalSession(
                    user_id=user_id,
                    strategy_id=strategy_ids[index],
                    exchange_account_id=account_ids[index],
                    symbol="BTC/USDT",
                    interval="1h",
                    execution_snapshot={"source_policy": "code_v1"},
                    is_active=phase == "active",
                )
                session.add(live)
                await session.flush()
                if phase != "active":
                    order = Order(
                        strategy_id=live.strategy_id,
                        exchange_account_id=live.exchange_account_id,
                        symbol=live.symbol,
                        side=OrderSide.buy,
                        type=OrderType.market,
                        quantity=D(2),
                        state=OrderState.submitted,
                    )
                    session.add(order)
                    await session.flush()
                    if phase == "inactive_risk":
                        # submit 전 commit 이후 IO/ACK가 아직 끝나지 않은 영속 소유권.
                        session.add(
                            LiveRiskState(
                                session_id=live.id,
                                direction="long",
                                entry_order_id=order.id,
                                expected_quantity=D(2),
                                reference_bars=[],
                                qty_step=D("0.1"),
                                min_qty=D("0.1"),
                                provisional_stop=D(90),
                            )
                        )
                        # risk 자체가 예약한다는 것을 entry order 검사와 분리해 증명한다.
                        order.state = OrderState.cancelled
                    else:
                        live.execution_snapshot = None
                    await session.flush()
            if index == 0:
                acquired.set()
                await release.wait()
            await session.commit()
            return allowed

    tasks = []
    try:
        tasks.append(asyncio.create_task(register(0)))
        await asyncio.wait_for(acquired.wait(), 5)
        tasks.append(asyncio.create_task(register(1)))
        done, _ = await asyncio.wait({tasks[1]}, timeout=0.05)
        assert not done
        release.set()
        assert await asyncio.wait_for(asyncio.gather(*tasks), 5) == [True, False]
    finally:
        release.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        async with maker() as cleanup:
            owned_sessions = (
                LiveSignalSession.__table__.select()
                .with_only_columns(LiveSignalSession.id)
                .where(LiveSignalSession.user_id == user_id)
            )
            await cleanup.execute(
                delete(LiveRiskState).where(LiveRiskState.session_id.in_(owned_sessions))
            )
            await cleanup.execute(delete(Order).where(Order.strategy_id.in_(strategy_ids)))
            await cleanup.execute(
                delete(LiveSignalSession).where(LiveSignalSession.user_id == user_id)
            )
            await cleanup.execute(delete(Strategy).where(Strategy.user_id == user_id))
            await cleanup.execute(delete(ExchangeAccount).where(ExchangeAccount.user_id == user_id))
            await cleanup.execute(delete(User).where(User.id == user_id))
            await cleanup.commit()

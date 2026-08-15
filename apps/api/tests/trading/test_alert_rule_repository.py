# loss-limit 알림이 세션 스코프로 손익을 합산하는지 검증한다

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEvent,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository, SessionScope

_START = datetime(2026, 7, 20, 6, 0, tzinfo=UTC)


async def _seed_user_strategy_account(
    db_session: AsyncSession, *, tag: str
) -> tuple[User, Strategy, ExchangeAccount]:
    user = User(
        auth_subject=f"{tag}-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()
    strategy = Strategy(
        user_id=user.id,
        name=f"{tag} scope",
        pine_source="//@version=5\nstrategy('scope')",
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
    return user, strategy, account


@pytest.mark.asyncio
async def test_sum_filled_realized_pnl_covers_orders_without_session_events(
    db_session: AsyncSession,
) -> None:
    """BL-444 — 이벤트 유무가 아니라 세션 스코프가 합계를 정한다.

    이 테스트의 이전 판은 `live_signal_events.order_id` 서브셀렉트를 전제로 "이벤트가
    붙은 주문만 센다" 를 고정하고 있었다. 그 전제가 바로 결함이었다 — 수동 청산과
    TV 웹훅은 이벤트를 남기지 않아 loss-limit 알림이 그 손실을 영영 못 봤다.
    이제 세션의 (전략, 계정, 심볼) + 창이 기준이고 이벤트는 무관하다.
    """
    user, strategy, account = await _seed_user_strategy_account(db_session, tag="alert-rule")

    target_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
        created_at=_START,
    )
    # 같은 (전략, 계정) 위 심볼만 다른 활성 세션 — partial unique 가 허용한다.
    other_symbol_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="ETHUSDT",
        interval=LiveSignalInterval.m5,
        created_at=_START,
    )
    db_session.add_all([target_session, other_symbol_session])
    await db_session.flush()

    def order(
        *,
        state: OrderState,
        pnl: str,
        filled_at: datetime | None,
        symbol: str = "BTCUSDT",
    ) -> Order:
        return Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol=symbol,
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=state,
            realized_pnl=Decimal(pnl),
            filled_at=filled_at,
        )

    dispatched = order(state=OrderState.filled, pnl="-5", filled_at=_START + timedelta(minutes=1))
    # 수동 청산 — 이벤트가 없다. 예전 event-join 은 이 손실을 통째로 놓쳤다.
    manual_close = order(state=OrderState.filled, pnl="-7", filled_at=_START + timedelta(minutes=2))
    before_window = order(state=OrderState.filled, pnl="-3", filled_at=_START - timedelta(hours=1))
    other_symbol = order(
        state=OrderState.filled,
        pnl="-11",
        filled_at=_START + timedelta(minutes=3),
        symbol="ETHUSDT",
    )
    unfilled = order(state=OrderState.submitted, pnl="-13", filled_at=None)
    db_session.add_all([dispatched, manual_close, before_window, other_symbol, unfilled])
    await db_session.flush()

    db_session.add(
        LiveSignalEvent(
            session_id=target_session.id,
            bar_time=_START,
            sequence_no=1,
            action="close",
            direction="long",
            trade_id="dispatched",
            qty=Decimal("1"),
            order_id=dispatched.id,
        )
    )
    await db_session.flush()

    repo = OrderRepository(db_session)
    # -5(이벤트 있음) + -7(이벤트 없음). 창 밖 -3, 타 심볼 -11, 미체결 -13 은 제외.
    assert (
        await repo.realized_pnl_split_for_session(SessionScope.from_live_session(target_session))
    ).total == Decimal("-12")
    # 심볼이 다른 세션은 자기 심볼 체결만 본다.
    assert (
        await repo.realized_pnl_split_for_session(
            SessionScope.from_live_session(other_symbol_session)
        )
    ).total == Decimal("-11")

    # 이벤트 기반 세션 역인덱스는 이번 변경과 무관하게 그대로 동작한다.
    session_repo = LiveSignalSessionRepository(db_session)
    found = await session_repo.find_active_by_order_id(dispatched.id)
    assert found is not None and found.id == target_session.id
    assert await session_repo.find_active_by_order_id(manual_close.id) is None


@pytest.mark.asyncio
async def test_closed_session_window_is_half_open_on_filled_at(
    db_session: AsyncSession,
) -> None:
    """BL-445 / D4 — 비활성 세션은 `[created_at, deactivated_at)` 안의 체결만 본다."""
    user, strategy, account = await _seed_user_strategy_account(db_session, tag="alert-window")

    ended = _START + timedelta(hours=1)
    closed_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
        is_active=False,
        created_at=_START,
        deactivated_at=ended,
    )
    db_session.add(closed_session)
    await db_session.flush()

    def order(*, pnl: str, filled_at: datetime) -> Order:
        return Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal(pnl),
            filled_at=filled_at,
        )

    db_session.add_all(
        [
            order(pnl="-5", filled_at=_START),  # 하한 포함
            order(pnl="-7", filled_at=ended - timedelta(seconds=1)),
            order(pnl="-9", filled_at=ended),  # 상한은 반열림이라 제외
            order(pnl="-11", filled_at=ended + timedelta(minutes=5)),  # 제외
        ]
    )
    await db_session.flush()

    assert (
        await OrderRepository(db_session).realized_pnl_split_for_session(
            SessionScope.from_live_session(closed_session)
        )
    ).total == Decimal("-12")

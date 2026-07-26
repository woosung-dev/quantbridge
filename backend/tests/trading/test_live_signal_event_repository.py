# 라이브 신호 이벤트 carry 집계의 실DB 창 경계를 검증한다.

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEvent,
    LiveSignalEventStatus,
    LiveSignalInterval,
    LiveSignalSession,
)
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository


@pytest.mark.asyncio
async def test_realized_pnl_sums_are_session_scoped_and_all_ignores_bar_time(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """carry는 창 경계를 지키고 화면 원장 합계는 모든 같은 세션 close를 센다."""
    window_start = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add(account)
    await db_session.flush()
    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    other_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="ETH/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add_all([session, other_session])
    await db_session.flush()
    db_session.add_all(
        [
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start - timedelta(minutes=1),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="before",
                qty=Decimal("1"),
                realized_pnl=Decimal("1.25"),
                status=LiveSignalEventStatus.failed,
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start,
                sequence_no=2,
                action="close",
                direction="long",
                trade_id="at-boundary",
                qty=Decimal("1"),
                realized_pnl=Decimal("9.99"),
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start + timedelta(minutes=1),
                sequence_no=3,
                action="close",
                direction="long",
                trade_id="after",
                qty=Decimal("1"),
                realized_pnl=Decimal("3.50"),
            ),
            LiveSignalEvent(
                session_id=session.id,
                bar_time=window_start - timedelta(minutes=2),
                sequence_no=4,
                action="entry",
                direction="long",
                trade_id="entry-null-pnl",
                qty=Decimal("1"),
            ),
            LiveSignalEvent(
                session_id=other_session.id,
                bar_time=window_start - timedelta(minutes=1),
                sequence_no=1,
                action="close",
                direction="long",
                trade_id="other-session",
                qty=Decimal("1"),
                realized_pnl=Decimal("99.99"),
            ),
        ]
    )
    await db_session.flush()

    repository = LiveSignalEventRepository(db_session)
    total_pnl, closed_count = await repository.sum_realized_pnl_before(
        session.id, bar_time=window_start
    )
    all_total_pnl, all_closed_count = await repository.sum_realized_pnl_all(session.id)

    assert total_pnl == Decimal("1.25")
    assert closed_count == 1
    assert all_total_pnl == Decimal("14.74")
    assert all_closed_count == 3

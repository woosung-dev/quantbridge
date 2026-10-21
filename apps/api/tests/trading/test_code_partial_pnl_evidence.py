"""코드 부분 체결 종결의 PnL 증거와 legacy 실패 추정값의 경계를 실제 SQL로 검증한다."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from uuid import uuid4

import pytest

from src.trading.models import (
    ExchangeAccount,
    ExchangeExit,
    ExchangeMode,
    ExchangeName,
    ExitAttribution,
    ExitClassification,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.order_fill_evidence import has_recorded_order_fill
from src.trading.repositories.order_repository import OrderRepository, SessionScope


@pytest.mark.asyncio
async def test_code_partial_fills_enter_pnl_sweep_cas_session_and_kill_switch_queries(
    db_session, user, strategy
):
    now = datetime.now(UTC)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
    )
    db_session.add(account)
    await db_session.flush()
    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval="1h",
        created_at=now - timedelta(minutes=1),
    )
    db_session.add(session)
    await db_session.flush()
    orders = []
    for index, (state, code, quantity) in enumerate(
        [
            (OrderState.cancelled, True, D("0.4")),
            (OrderState.rejected, True, D("0.6")),
            (OrderState.rejected, False, D("0.4")),
            (OrderState.cancelled, True, D(0)),
        ]
    ):
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol=session.symbol,
            side=OrderSide.sell,
            type=OrderType.limit,
            quantity=D(1),
            state=state,
            filled_quantity=quantity,
            filled_price=D(100),
            filled_at=now,
            leverage=1,
            reduce_only=True,
            exchange_order_id=f"partial-{index}",
            risk_context={"session_id": str(session.id), "generation": 1, "role": "partial_tp"}
            if code
            else None,
            realized_pnl=D(-999) if index > 1 else None,
        )
        orders.append(order)
        db_session.add(order)
        db_session.add(
            ExchangeExit(
                exchange_account_id=account.id,
                exchange_order_id=order.exchange_order_id,
                row_hash=uuid4().hex,
                symbol="BTCUSDT",
                side="Sell",
                closed_pnl=D(-index - 3),
                exchange_created_at=now,
                classification=ExitClassification.ours,
                attribution_confidence=ExitAttribution.exact,
                raw={},
            )
        )
    await db_session.commit()
    repo = OrderRepository(db_session)
    expected = {order.id for order in orders[:2]}
    assert [has_recorded_order_fill(order) for order in orders] == [True, True, False, False]
    assert {
        order.id for order in await repo.list_unsynced_with_exchange_exit(account.id)
    } == expected
    assert {
        order.id
        for order in await repo.list_by_exchange_order_ids(
            account.id, [o.exchange_order_id for o in orders]
        )
    } == expected
    assert {order.id for order in await repo.list_filled_for_attribution(account.id)} == expected
    for index, order in enumerate(orders):
        changed = await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=D(-index - 3), synced_at=now
        )
        assert changed == (1 if index < 2 else 0)
    await repo.commit()
    assert await repo.sum_filled_realized_pnl_by_strategy(strategy.id) == D(-7)
    assert await repo.sum_filled_realized_pnl_by_account_in_window(
        account.id, started_at=now - timedelta(seconds=1), ended_at=now + timedelta(seconds=1)
    ) == D(-7)
    assert (await repo.get_daily_summary(now.date()))[0] == D(-7)
    scope = SessionScope.from_live_session(session)
    assert {order.id for order in await repo.list_filled_realized_for_session(scope)} == expected
    split = await repo.realized_pnl_split_for_session(scope)
    assert split.confirmed == D(-7) and split.confirmed_count == 2 and split.estimated == 0
    assert await repo.list_unsynced_with_exchange_exit(account.id) == []
    assert await repo.list_synced_with_exchange_exit(account.id) == []
    assert (
        await repo.resync_exchange_realized_pnl(orders[0].id, realized_pnl=D(-5), synced_at=now)
        == 1
    )
    assert (
        await repo.resync_exchange_realized_pnl(orders[0].id, realized_pnl=D(-5), synced_at=now)
        == 0
    )
    assert (
        await repo.resync_exchange_realized_pnl(orders[2].id, realized_pnl=D(-5), synced_at=now)
        == 0
    )
    await repo.commit()
    assert {order.id for order in await repo.list_synced_with_exchange_exit(account.id)} == {
        orders[0].id
    }

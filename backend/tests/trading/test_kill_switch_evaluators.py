"""KillSwitch evaluator 단독 검증 — timing 없는 결정적 probe."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


@pytest.fixture
async def strat_account(db_session, user, strategy):
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    return strategy, acc


async def _make_filled_order(
    db_session, strategy, account, *, pnl: Decimal, filled_at: datetime
):
    o = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.filled,
        realized_pnl=pnl,
        filled_at=filled_at,
    )
    db_session.add(o)
    await db_session.flush()
    return o


async def test_cumulative_loss_evaluator_not_gated_when_below_threshold(
    db_session, strat_account
):
    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repository import OrderRepository

    strategy, account = strat_account
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-50"), filled_at=datetime.now(UTC)
    )

    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),
    )
    result = await ev.evaluate(
        EvaluationContext(strategy.id, account.id, datetime.now(UTC))
    )

    assert result.gated is False


async def test_cumulative_loss_evaluator_gated_when_exceeds(db_session, strat_account):
    from src.trading.kill_switch import CumulativeLossEvaluator, EvaluationContext
    from src.trading.repository import OrderRepository

    strategy, account = strat_account
    # 누적 손실 -$1,500 / capital $10,000 = 15% > threshold 10%
    await _make_filled_order(
        db_session,
        strategy,
        account,
        pnl=Decimal("-1500"),
        filled_at=datetime.now(UTC),
    )

    ev = CumulativeLossEvaluator(
        OrderRepository(db_session),
        threshold_percent=Decimal("10"),
        capital_base=Decimal("10000"),
    )
    result = await ev.evaluate(
        EvaluationContext(strategy.id, account.id, datetime.now(UTC))
    )

    assert result.gated is True
    assert result.trigger_type == "cumulative_loss"
    assert result.trigger_value == Decimal("15.00")
    assert result.threshold == Decimal("10")


async def test_daily_loss_evaluator_sums_today_only(db_session, strat_account):
    """UTC 당일 realized PnL 합만 집계 — 어제 주문은 포함 안 됨."""
    from src.trading.kill_switch import DailyLossEvaluator, EvaluationContext
    from src.trading.repository import OrderRepository

    strategy, account = strat_account
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)

    # 어제 -$1000 (당일 집계에서 제외)
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-1000"), filled_at=yesterday
    )
    # 오늘 -$400 (< threshold $500)
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-400"), filled_at=now
    )

    ev = DailyLossEvaluator(OrderRepository(db_session), threshold_usd=Decimal("500"))
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, now))

    assert result.gated is False


async def test_daily_loss_evaluator_gated_when_today_exceeds(db_session, strat_account):
    from src.trading.kill_switch import DailyLossEvaluator, EvaluationContext
    from src.trading.repository import OrderRepository

    strategy, account = strat_account
    now = datetime.now(UTC)

    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-300"), filled_at=now
    )
    await _make_filled_order(
        db_session, strategy, account, pnl=Decimal("-300"), filled_at=now
    )

    ev = DailyLossEvaluator(OrderRepository(db_session), threshold_usd=Decimal("500"))
    result = await ev.evaluate(EvaluationContext(strategy.id, account.id, now))

    assert result.gated is True
    assert result.trigger_type == "daily_loss"
    assert result.trigger_value == Decimal("-600")
    assert result.threshold == Decimal("500")

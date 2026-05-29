"""MP-1 (2/2) — realized_pnl 쓰기 경로.

close 이벤트의 realized PnL 이 Order.realized_pnl 에 기록되고 fill 전이에서 보존되어야
kill-switch CumulativeLoss/DailyLoss 평가기(SUM(Order.realized_pnl))가 실제로 작동한다.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.exceptions import KillSwitchActive
from src.trading.kill_switch import EvaluationResult, KillSwitchService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import OrderRequest
from src.trading.services.order_service import OrderService


async def _account(db_session: AsyncSession, user) -> ExchangeAccount:
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


class _NoopKillSwitch:
    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        return None


class _Dispatcher:
    async def dispatch_order_execution(self, order_id: UUID) -> None:
        return None


async def test_transition_to_filled_preserves_realized_pnl(
    db_session: AsyncSession, strategy, user
):
    """MP-1: fill 전이가 생성 시점 realized_pnl 을 NULL 로 덮어쓰지 않아야 한다."""
    account = await _account(db_session, user)
    repo = OrderRepository(db_session)
    order = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("0.01"),
            state=OrderState.submitted,
            realized_pnl=Decimal("-50"),  # close 주문 — 손실 -50
        )
    )
    await repo.commit()

    # realized_pnl 인자 없이 fill 전이 (live_signal / ws / reconciler 의 4 call-site 패턴)
    rowcount = await repo.transition_to_filled(
        order.id,
        exchange_order_id="bybit-99",
        filled_price=Decimal("49000"),
        filled_at=datetime.now(UTC),
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.realized_pnl == Decimal("-50"), (
        f"fill 전이가 realized_pnl 을 덮어씀: {fetched.realized_pnl}"
    )


async def test_order_service_persists_request_realized_pnl(
    db_session: AsyncSession, strategy, user
):
    """MP-1: OrderRequest.realized_pnl 이 생성된 Order 에 기록된다 (dispatch 경로 전파)."""
    account = await _account(db_session, user)
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_Dispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
        realized_pnl=Decimal("-75.5"),
    )
    await svc.execute(req, idempotency_key=None)

    order = (
        await db_session.execute(select(Order).where(Order.strategy_id == strategy.id))
    ).scalar_one()
    assert order.realized_pnl == Decimal("-75.5")


class _ForceGated:
    async def evaluate(self, ctx):
        return EvaluationResult(
            gated=True,
            trigger_type="daily_loss",
            trigger_value=Decimal("-600"),
            threshold=Decimal("500"),
        )


async def test_kill_switch_event_persists_after_gated_order(
    db_session: AsyncSession, strategy, user
):
    """ASYNC-1: gated 주문 시 생성된 kill-switch 이벤트가 OrderService savepoint rollback 으로
    유실되지 않고 persist 되어야 한다 (이전엔 begin_nested 안에서 INSERT→raise→rollback →
    audit row 유실 + 매 주문 재평가 alert storm). manual commit 없이 조회되어야 함.
    """
    account = await _account(db_session, user)
    ks_repo = KillSwitchEventRepository(db_session)
    ks = KillSwitchService(evaluators=[_ForceGated()], events_repo=ks_repo)
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_Dispatcher(),
        kill_switch=ks,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
    )

    with pytest.raises(KillSwitchActive):
        await svc.execute(req, idempotency_key=None)

    # manual commit 없이 — 서비스가 이벤트를 durable 하게 commit 했어야 함
    active = await ks_repo.get_active(strategy_id=strategy.id, account_id=account.id)
    assert active is not None, "kill-switch 이벤트가 savepoint rollback 으로 유실됨 (ASYNC-1)"

    count = (
        await db_session.execute(select(func.count()).select_from(Order))
    ).scalar_one()
    assert count == 0, "gated 주문이 생성됨"

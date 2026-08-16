# loss-limit 태스크가 실 DB 에서 세션 스코프 합계로 발화하는지 종단 검증한다

"""BL-444 종단 테스트.

`test_alert_rules_task.py` 는 리포지터리를 통째로 가짜로 바꾸므로 **쿼리 자체가
틀려도 통과한다** — BL-453 의 재조회 크래시가 유닛테스트를 빠져나간 것과 같은
사각지대다. 여기서는 리포지터리와 DB 를 진짜로 쓰고 Redis 락과 잔고 조회, 발송만
가짜로 둔다.

판별력 — 임계 10% · 자본 100 USDT 에서
- 이벤트가 붙은 주문만 세면 -5 → 5.00% → **발화 안 함** (fix 전 동작)
- 세션 스코프로 세면 -5 + -7(수동 청산, 이벤트 없음) → 12.00% → **발화**

즉 이 테스트는 수동 청산이 합계에 들어올 때만 통과한다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    AlertChannel,
    AlertRule,
    AlertRuleType,
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

_START = datetime(2026, 7, 20, 6, 0, tzinfo=UTC)


class _Redis:
    def __init__(self) -> None:
        self.keys: set[bytes] = set()

    async def set(self, key, _value, *, nx=False, ex=None):  # type: ignore[no-untyped-def]
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


@pytest.mark.asyncio
async def test_loss_rule_counts_manual_close_without_event(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.tasks.alert_rules as task

    user = User(
        auth_subject=f"alert-e2e-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()
    strategy = Strategy(
        user_id=user.id,
        name="alert e2e",
        pine_source="//@version=5\nstrategy('e2e')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    live_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m5,
        created_at=_START,
    )
    db_session.add(live_session)
    await db_session.flush()
    db_session.add(
        AlertRule(
            session_id=live_session.id,
            rule_type=AlertRuleType.loss_limit,
            channel=AlertChannel.slack,
            threshold_percent=Decimal("10"),
        )
    )

    def _order(pnl: str, minutes: int) -> Order:
        return Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal(pnl),
            filled_at=_START + timedelta(minutes=minutes),
        )

    dispatched = _order("-5", 1)
    manual_close = _order("-7", 2)  # 이벤트 없음 — fix 전에는 안 보였다
    db_session.add_all([dispatched, manual_close])
    await db_session.flush()
    db_session.add(
        LiveSignalEvent(
            session_id=live_session.id,
            bar_time=_START,
            sequence_no=1,
            action="close",
            direction="long",
            trade_id="dispatched",
            qty=Decimal("1"),
            order_id=dispatched.id,
        )
    )
    await db_session.commit()

    @asynccontextmanager
    async def _sm():
        yield db_session

    class _Accounts:
        def __init__(self, *_args: object) -> None:
            pass

        async def fetch_balance_usdt(self, _account_id: object) -> Decimal:
            return Decimal("100")

    sent: list[dict[str, object]] = []

    async def _send(_settings: object, **kwargs: object) -> dict[str, bool]:
        sent.append(kwargs)
        return {"slack": True}

    class _Engine:
        async def dispose(self) -> None:
            return None

    monkeypatch.setattr(task, "create_worker_engine_and_sm", lambda: (_Engine(), _sm))
    monkeypatch.setattr(task, "ExchangeAccountService", _Accounts)
    monkeypatch.setattr(task, "_get_redis_lock_pool_for_alert", _Redis)
    monkeypatch.setattr(task, "send_rule_alert", _send)

    assert await task._async_evaluate_loss_rules() == {"evaluated": 1, "fired": 1}
    assert sent, "수동 청산이 합계에 들어와야 12% 로 임계를 넘는다"
    context = sent[0]["context"]
    assert isinstance(context, dict)
    # 실 DB 는 Numeric(18,8) 이라 "-12.00000000" 로 온다 — 가짜 리포지터리는 이 차이를
    # 절대 드러내지 못한다. 문자열이 아니라 값으로 비교한다.
    assert Decimal(str(context["total_realized_pnl"])) == Decimal("-12")
    assert context["loss_percent"] == "12.00"

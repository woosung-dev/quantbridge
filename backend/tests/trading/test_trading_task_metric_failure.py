"""B2/B3/B4 — `tasks/trading.py` 의 raw `qb_active_orders.dec()` 고장 주입 (BL-580).

★**BL-580 이 이 셋을 뺀 근거는 코드 독해였다** — 「거절·취소 확정 뒤라 실패로 계상하는
`except` 가 없다. 던지면 task FAILED + gauge drift 이고 후속 훅 유실이 없다」.
후반부(후속 훅 유실 없음)는 주입으로 **참**임이 확인됐다. 전반부는 **그것이 무해하다는
뜻이 아니다** — terminal 전이는 `commit()` 으로 이미 확정됐는데 task 는 FAILED 로 남는다.
즉 **성공한 외부 작용이 실패로 기록된다**(사전등록 H1).

사전등록 postcondition (`dev-log/2026-08-03-metric-guard-residual.md` §1.2b):
B2 `{"state": "rejected"}` · B3 `{"state": "cancelled"}` · B4 `{"state": "cancelled"}` 반환.

★같은 파일의 다른 `qb_active_orders.dec()` 4곳은 이미 `record_metric_safely` 로 감싸져 있다
(`:386` `:450` `:496` `:558`). 셋만 raw 로 남기면 **잘못된 패턴이 복제된다** —
직전 회차가 `_PROTECTED_SITES` 에 같은 이유를 적어 뒀다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
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
async def submitted_order(db_session: AsyncSession):
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(id=uuid4(), clerk_user_id=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@t.local")
    db_session.add(user)
    await db_session.flush()
    strategy = Strategy(
        user_id=user.id,
        name="metric-failure",
        pine_source="//@version=5\nstrategy('m')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test-k"),
        api_secret_encrypted=crypto.encrypt("test-s"),
        label="metric failure acc",
    )
    db_session.add(account)
    await db_session.flush()
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.submitted,
        submitted_at=datetime.now(UTC),
        exchange_order_id="bybit-metric-1",
    )
    db_session.add(order)
    await db_session.commit()
    return order, account


class _NoopEngine:
    async def dispose(self) -> None:
        return None


def _fake_create_worker_engine_and_sm(db_session: AsyncSession):
    @asynccontextmanager
    async def _ctx():
        yield db_session

    class _SM:
        def __call__(self):
            return _ctx()

    def _factory():
        return _NoopEngine(), _SM()

    return _factory


class _CancellingProvider:
    async def cancel_order(self, creds, exchange_order_id: str, symbol: str) -> None:
        return None


def _explode_dec(calls: list[str]):
    def _dec(*_args: object, **_kwargs: object) -> None:
        calls.append("dec")
        raise OSError("mmap allocation failed")

    return _dec


@pytest.mark.parametrize(
    ("fetch_status", "expected_state"),
    [("rejected", "rejected"), ("cancelled", "cancelled")],
)
@pytest.mark.asyncio
async def test_watchdog_terminal_transition_survives_gauge_failure(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
    fetch_status: str,
    expected_state: str,
) -> None:
    """B2/B3 (`trading.py:908` · `:931`) — watchdog 의 거절·취소 확정 뒤 gauge 실패.

    확정 전이는 `session.commit()` 으로 이미 내구화됐고 `publish_realtime` 도 나갔다.
    그 **뒤**의 계측이 task 를 죽이면 원장은 맞는데 실행 기록만 FAILED 다.
    """
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _account = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override=fetch_status
        ),
    )
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())
    calls: list[str] = []
    monkeypatch.setattr(task_mod.qb_active_orders, "dec", _explode_dec(calls))

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert calls == ["dec"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["state"] == expected_state
    await db_session.refresh(order)
    assert order.state == OrderState(expected_state)


@pytest.mark.asyncio
async def test_exchange_cancel_result_survives_gauge_failure(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B4 (`trading.py:1093`) — 거래소 취소 성공 + DB 확정 뒤 gauge 실패.

    ★여기서 던지면 바로 다음 줄의 `order_cancelled_on_exchange` 로그도 유실된다.
    거래소에서 실제로 취소된 사실을 남기는 유일한 라인이다.
    """
    import src.tasks.trading as task_mod

    order, _account = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod, "_provider_for_account_and_leverage", lambda e, m, h: _CancellingProvider()
    )
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())
    calls: list[str] = []
    monkeypatch.setattr(task_mod.qb_active_orders, "dec", _explode_dec(calls))

    result = await task_mod._async_cancel_order(order.id)

    assert calls == ["dec"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert result["state"] == "cancelled"
    await db_session.refresh(order)
    assert order.state == OrderState.cancelled

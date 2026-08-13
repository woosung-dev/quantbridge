# 비활성 세션의 조건부 진입 스윕 태스크를 검증한다.

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401
from src.auth.models import User
from src.common.metrics import (
    qb_live_conditional_reconcile_errors_total,
    qb_live_conditional_sweep_filled_total,
)
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
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

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]


class _NoopEngine:
    async def dispose(self) -> None:
        return None


def _fake_create_worker_engine_and_sm(db_session: AsyncSession):
    @asynccontextmanager
    async def _context():
        yield db_session

    class _SessionMaker:
        def __call__(self):
            return _context()

    return lambda: (_NoopEngine(), _SessionMaker())


def _patch_sweeper(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession, provider: type[object]
) -> MagicMock:
    # ★BL-583 — 아래 `src.trading.registry.dispatch` 패치는 **정의 모듈**을 갈아치운다. 그 창
    #   안에서 `src.tasks.trading` 이 **처음** 적재되면(스윕이 밟는 지연 import) 그 모듈 최상단의
    #   `from src.trading.registry import dispatch as _dispatch_provider`(`trading.py:86`)가
    #   MagicMock 을 자기 전역으로 **복사**하고, monkeypatch 는 정의 모듈만 되돌리므로 그
    #   복사본이 세션 끝까지 남는다(실측: 이 파일 단독 실행에서 가드가 잡았다).
    from src.tasks import trading as _preload_trading  # noqa: F401

    dispatch = MagicMock(return_value=provider())
    monkeypatch.setattr(
        live_signal_module,
        "create_worker_engine_and_sm",
        _fake_create_worker_engine_and_sm(db_session),
    )
    monkeypatch.setattr("src.trading.registry.dispatch", dispatch)
    return dispatch


@pytest.fixture
async def conditional_entry_factory(db_session: AsyncSession):
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@s.local",
    )
    strategy = Strategy(
        user_id=user.id,
        name="conditional-sweeper",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("key"),
        api_secret_encrypted=crypto.encrypt("secret"),
        label="conditional-sweeper",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(strategy)
    await db_session.flush()
    db_session.add(account)
    await db_session.flush()

    async def _make(*, active: bool, valid_key: bool = True) -> Order:
        session = LiveSignalSession(
            user_id=user.id,
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            interval=LiveSignalInterval.m1,
            is_active=active,
            deactivated_at=None if active else datetime.now(UTC),
        )
        db_session.add(session)
        await db_session.flush()
        key = (
            f"live:{session.id}:cond:1:100:0.001:entry"
            if valid_key
            else "external-conditional-order"
        )
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            state=OrderState.submitted,
            trigger_price=Decimal("100"),
            exchange_order_id=f"exchange-{uuid4()}",
            idempotency_key=key,
            submitted_at=datetime.now(UTC),
        )
        db_session.add(order)
        await db_session.flush()
        return order

    # ★sweeper 프로덕션 경로가 `commit()` 을 하므로 테스트 트랜잭션 격리가 깨진다.
    # 정리하지 않으면 여기서 만든 user/strategy 행이 남아 다른 테스트(전략 페이지네이션
    # 등)의 카운트를 흔든다 - 실측으로 랜덤 순서에서 3건이 flake 났다.
    # ★id 를 yield 전에 확보한다. rollback 은 ORM 객체를 expire 시키므로 그 뒤에
    # `strategy.id` 를 읽으면 lazy refresh 가 MissingGreenlet 을 낸다 - 프로덕션
    # sweeper 에서 고친 것과 같은 함정이다.
    strategy_id, account_id, user_id = strategy.id, account.id, user.id
    yield _make
    await db_session.rollback()
    await db_session.execute(delete(Order).where(Order.strategy_id == strategy_id))
    await db_session.execute(
        delete(LiveSignalSession).where(LiveSignalSession.strategy_id == strategy_id)
    )
    await db_session.execute(delete(ExchangeAccount).where(ExchangeAccount.id == account_id))
    await db_session.execute(delete(Strategy).where(Strategy.id == strategy_id))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_sweeper_cancels_only_inactive_owned_conditional_entries(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inactive = await conditional_entry_factory(active=False)
    active = await conditional_entry_factory(active=True)
    foreign = await conditional_entry_factory(active=False, valid_key=False)
    await db_session.commit()

    cancelled_exchange_ids: list[str] = []

    class _Provider:
        async def cancel_order(self, _creds: Any, exchange_order_id: str, _symbol: str) -> None:
            cancelled_exchange_ids.append(exchange_order_id)

    dispatch = _patch_sweeper(monkeypatch, db_session, _Provider)

    result = await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(inactive)
    await db_session.refresh(active)
    await db_session.refresh(foreign)

    assert result == {"cancelled": 1}
    assert cancelled_exchange_ids == [inactive.exchange_order_id]
    assert inactive.state == OrderState.cancelled
    assert active.state == OrderState.submitted
    assert foreign.state == OrderState.submitted
    dispatch.assert_called_once_with(ExchangeName.bybit, ExchangeMode.demo, False)


@pytest.mark.asyncio
async def test_sweeper_logs_and_metrics_provider_cancel_failure(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orphan = await conditional_entry_factory(active=False)
    await db_session.commit()

    class _FailingProvider:
        async def cancel_order(self, _creds: Any, _exchange_order_id: str, _symbol: str) -> None:
            raise RuntimeError("provider unavailable")

        async def fetch_order_by_client_id(
            self, _creds: Any, _client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> Any:
            assert trigger is True
            raise RuntimeError("provider unavailable")

    _patch_sweeper(monkeypatch, db_session, _FailingProvider)
    metric = qb_live_conditional_reconcile_errors_total.labels(stage="sweep_cancel")
    before = metric._value.get()

    result = await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(orphan)

    assert result == {"cancelled": 0}
    assert metric._value.get() == before + 1
    assert orphan.state == OrderState.submitted


@pytest.mark.asyncio
async def test_sweeper_uses_conditional_probe_after_cancel_failure(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orphan = await conditional_entry_factory(active=False)
    await db_session.commit()

    class _Provider:
        async def cancel_order(self, _creds: Any, _exchange_order_id: str, _symbol: str) -> None:
            raise RuntimeError("cancel raced with fill")

        async def fetch_order_by_client_id(
            self, _creds: Any, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> Any:
            assert client_order_id == str(orphan.id)
            assert trigger is True
            return SimpleNamespace(
                exchange_order_id=orphan.exchange_order_id,
                status="filled",
                filled_price=Decimal("101"),
                filled_quantity=Decimal("0.001"),
            )

    from src.tasks import trading as trading_module

    trailing = MagicMock()
    closed_pnl = MagicMock()
    monkeypatch.setattr(trading_module, "_enqueue_trailing_if_intended", trailing)
    monkeypatch.setattr(trading_module, "_enqueue_closed_pnl_refresh", closed_pnl)
    # BL-562 — 반전 계측 helper 는 **가짜로 덮지 않는다**. helper 의 조건부-진입 게이트를
    # 실제로 지나야 `hook_order` 의 key 누락(= 이 경로 조용히 미계측)이 드러난다.
    reversal_enqueued: list[dict] = []
    monkeypatch.setattr(
        trading_module.measure_conditional_reversal_task,
        "apply_async",
        lambda **kw: reversal_enqueued.append(kw),
    )
    _patch_sweeper(monkeypatch, db_session, _Provider)
    filled_metric = qb_live_conditional_sweep_filled_total
    before = filled_metric._value.get()

    result = await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(orphan)

    assert result == {"cancelled": 0}
    assert orphan.state == OrderState.filled
    assert orphan.filled_price == Decimal("101")
    assert filled_metric._value.get() == before + 1
    trailing.assert_called_once()
    closed_pnl.assert_called_once()
    assert [kw["args"] for kw in reversal_enqueued] == [[str(orphan.id)]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "filled_quantity", "expected_state"),
    [
        ("cancelled", Decimal("0.0005"), OrderState.cancelled),
        ("rejected", Decimal("0.0005"), OrderState.rejected),
        ("cancelled", None, OrderState.cancelled),
        ("cancelled", Decimal("0"), OrderState.cancelled),
    ],
)
async def test_sweeper_terminal_probe_records_only_nonzero_partial_fill(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    filled_quantity: Decimal | None,
    expected_state: OrderState,
) -> None:
    orphan = await conditional_entry_factory(active=False)
    await db_session.commit()

    class _Provider:
        async def cancel_order(self, _creds: Any, _exchange_order_id: str, _symbol: str) -> None:
            raise RuntimeError("cancel raced with terminal transition")

        async def fetch_order_by_client_id(
            self, _creds: Any, _client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> Any:
            assert trigger is True
            return SimpleNamespace(
                exchange_order_id=orphan.exchange_order_id,
                status=status,
                filled_price=Decimal("101") if filled_quantity else None,
                filled_quantity=filled_quantity,
            )

    _patch_sweeper(monkeypatch, db_session, _Provider)

    await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(orphan)

    assert orphan.state == expected_state
    assert orphan.filled_quantity == (filled_quantity if filled_quantity else None)
    assert orphan.filled_price == (Decimal("101") if filled_quantity else None)


@pytest.mark.asyncio
async def test_sweeper_reports_live_probe_after_cancel_failure(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    orphan = await conditional_entry_factory(active=False)
    await db_session.commit()

    class _Provider:
        async def cancel_order(self, _creds: Any, _exchange_order_id: str, _symbol: str) -> None:
            raise RuntimeError("cancel failed")

        async def fetch_order_by_client_id(
            self, _creds: Any, _client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> Any:
            assert trigger is True
            return SimpleNamespace(
                exchange_order_id=orphan.exchange_order_id,
                status="submitted",
                filled_price=None,
                filled_quantity=None,
            )

    _patch_sweeper(monkeypatch, db_session, _Provider)
    metric = qb_live_conditional_reconcile_errors_total.labels(stage="sweep_cancel_stalled")
    before = metric._value.get()
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    result = await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(orphan)

    assert result == {"cancelled": 0}
    assert orphan.state == OrderState.submitted
    assert metric._value.get() == before + 1
    assert "live_conditional_entry_sweep_cancel_stalled" in caplog.messages


@pytest.mark.asyncio
async def test_sweeper_failure_does_not_stop_later_snapshot(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = await conditional_entry_factory(active=False)
    second = await conditional_entry_factory(active=False)
    first.submitted_at = datetime(2026, 1, 1, tzinfo=UTC)
    second.submitted_at = datetime(2026, 1, 1, 0, 1, tzinfo=UTC)
    first_id, second_id, first_exchange_order_id = (
        first.id,
        second.id,
        first.exchange_order_id,
    )
    await db_session.commit()

    class _Provider:
        async def cancel_order(self, _creds: Any, exchange_order_id: str, _symbol: str) -> None:
            if exchange_order_id == first_exchange_order_id:
                raise RuntimeError("first cancel fails")

        async def fetch_order_by_client_id(
            self, _creds: Any, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> None:
            assert client_order_id == str(first_id)
            raise RuntimeError("first probe fails")

    _patch_sweeper(monkeypatch, db_session, _Provider)

    result = await live_signal_module._async_sweep_conditional_entries()
    first_after = await db_session.get(Order, first_id)
    second_after = await db_session.get(Order, second_id)

    assert result == {"cancelled": 1}
    assert first_after is not None and first_after.state == OrderState.submitted
    assert second_after is not None and second_after.state == OrderState.cancelled


def test_conditional_entry_sweeper_beat_schedule() -> None:
    schedule = celery_module.celery_app.conf.beat_schedule
    entry = schedule["sweep-orphan-conditional-entries"]

    assert entry["task"] == "live_signal.sweep_conditional_entries"
    assert entry["schedule"] == 300.0
    assert entry["options"]["expires"] == 240
    assert "live_signal.sweep_conditional_entries" in celery_module.celery_app.tasks


def test_every_deactivation_site_enqueues_conditional_sweep() -> None:
    """★세션이 죽는 모든 경로가 조건부 진입 청소를 요청해야 한다.

    이걸 놓치면 "엔진을 못 믿겠다" 고 판단한 바로 그 순간에 거래소 주문을 남긴다 -
    fail-closed 의 정반대다. 비활성화 경로는 앞으로도 늘어날 수 있으므로 호출처를
    소스에서 세어 래칫으로 고정한다(경로별 무거운 하네스 4벌보다 이쪽이 정직하다).
    """
    from pathlib import Path

    source = Path(live_signal_module.__file__).read_text(encoding="utf-8")
    lines = source.splitlines()
    deactivate_lines = [i for i, line in enumerate(lines) if "sess_repo.deactivate(" in line]

    assert deactivate_lines, "deactivate 호출처를 못 찾았다 - 이 테스트가 stale 이다"
    for index in deactivate_lines:
        window = "\n".join(lines[index : index + 8])
        assert "_enqueue_conditional_entry_sweep()" in window, (
            f"{index + 1} 행의 deactivate 뒤에 조건부 진입 청소 요청이 없다"
        )

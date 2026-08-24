# 조건부 진입 janitor가 거래소 확인 뒤에만 상태를 수리하거나 종결하는지 검증한다.

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.common.metrics import qb_live_conditional_reconcile_errors_total
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.tasks import conditional_entry_janitor as janitor_module
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
from src.trading.providers import OrderStatusFetch
from src.trading.services.conditional_entry_planner import build_conditional_entry_key


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


@pytest.fixture
async def conditional_entry_factory(db_session: AsyncSession):
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@janitor.local",
    )
    strategy = Strategy(
        user_id=user.id,
        name="conditional-entry-janitor",
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
        label="conditional-entry-janitor",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(strategy)
    await db_session.flush()
    db_session.add(account)
    await db_session.flush()

    async def _make(
        *,
        exchange_order_id: str | None,
        submitted_at: datetime | None = None,
    ) -> Order:
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            state=OrderState.submitted,
            trigger_price=Decimal("100"),
            exchange_order_id=exchange_order_id,
            # ★janitor 가 쓸어담는 것은 **우리가 등재한 조건부 진입**이다. 그러면 key 도
            #   그 형식이어야 한다 — 임의 문자열이면 key 를 읽는 소비자(BL-562 반전 계측)가
            #   프로덕션에서는 못 알아보는데 테스트만 통과한다.
            idempotency_key=build_conditional_entry_key(
                uuid4(),
                f"entry-{uuid4()}",
                datetime(2026, 7, 31, 11, 0, tzinfo=UTC),
                Decimal("100"),
                Decimal("0.001"),
            ),
            submitted_at=submitted_at or datetime.now(UTC) - timedelta(minutes=31),
        )
        db_session.add(order)
        await db_session.flush()
        return order

    strategy_id = strategy.id
    account_id = account.id
    user_id = user.id
    yield _make
    await db_session.rollback()
    await db_session.execute(delete(Order).where(Order.strategy_id == strategy_id))
    await db_session.execute(delete(ExchangeAccount).where(ExchangeAccount.id == account_id))
    await db_session.execute(delete(Strategy).where(Strategy.id == strategy_id))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.commit()


def _patch_task(
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
    provider: type[object],
) -> tuple[MagicMock, MagicMock]:
    dec = MagicMock()
    dispatch = MagicMock(return_value=provider())
    monkeypatch.setattr(
        janitor_module,
        "create_worker_engine_and_sm",
        _fake_create_worker_engine_and_sm(db_session),
    )
    monkeypatch.setattr("src.trading.registry.dispatch", dispatch)
    monkeypatch.setattr(janitor_module, "qb_active_orders", SimpleNamespace(dec=dec))
    return dec, dispatch


@pytest.mark.asyncio
async def test_janitor_rejects_missing_form_one_and_decrements_gauge(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = await conditional_entry_factory(exchange_order_id=None)
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> None:
            assert client_order_id == str(order.id)
            assert trigger is True
            return None

    dec, _ = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert result == {"repaired": 0, "rejected": 1, "terminal": 0}
    assert order.state == OrderState.rejected
    dec.assert_called_once()


@pytest.mark.asyncio
async def test_janitor_repairs_form_one_when_client_id_query_finds_live_order(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = await conditional_entry_factory(exchange_order_id=None)
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, _client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> OrderStatusFetch:
            assert trigger is True
            return OrderStatusFetch(
                exchange_order_id="exchange-live",
                status="submitted",
                filled_price=None,
                filled_quantity=None,
                raw={},
            )

    dec, _ = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert result == {"repaired": 1, "rejected": 0, "terminal": 0}
    assert order.state == OrderState.submitted
    assert order.exchange_order_id == "exchange-live"
    dec.assert_not_called()


@pytest.mark.asyncio
async def test_janitor_transitions_form_two_only_after_terminal_probe(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = await conditional_entry_factory(exchange_order_id="exchange-ghost")
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> OrderStatusFetch:
            assert client_order_id == str(order.id)
            assert trigger is True
            return OrderStatusFetch(
                exchange_order_id="exchange-ghost",
                status="filled",
                filled_price=Decimal("101"),
                filled_quantity=Decimal("0.001"),
                raw={},
            )

    from src.tasks import trading as trading_module

    trailing = MagicMock()
    closed_pnl = MagicMock()
    monkeypatch.setattr(trading_module, "_enqueue_trailing_if_intended", trailing)
    monkeypatch.setattr(trading_module, "_enqueue_closed_pnl_refresh", closed_pnl)
    # BL-562 — 반전 계측은 helper 를 **가짜로 바꾸지 않고** 실제로 통과시킨다.
    # ★1차에는 여기를 `MagicMock` 으로 덮었고, 그래서 janitor 의 `hook_order` 에
    #   `idempotency_key` 가 아예 없다는 사실(= 이 경로가 조용히 미계측)을 **테스트가
    #   못 잡았다**. 가짜는 helper 의 게이트를 안 지난다 — 게이트를 지나게 하려면
    #   최종 부작용인 `apply_async` 를 잡아야 한다.
    reversal_enqueued: list[dict] = []
    monkeypatch.setattr(
        trading_module.measure_conditional_reversal_task,
        "apply_async",
        lambda **kw: reversal_enqueued.append(kw),
    )
    dec, dispatch = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert result == {"repaired": 0, "rejected": 0, "terminal": 1}
    assert order.state == OrderState.filled
    assert order.filled_price == Decimal("101")
    dec.assert_called_once()
    dispatch.assert_called_once_with(ExchangeName.bybit, ExchangeMode.demo, False)
    trailing.assert_called_once()
    closed_pnl.assert_called_once()
    # ★실제 helper 를 지나 예약까지 갔는가. `hook_order` 에 `idempotency_key` 를 빼면
    #   helper 가 조건부 진입으로 못 알아보고 조용히 return 해 이 단언이 깨진다.
    assert [kw["args"] for kw in reversal_enqueued] == [[str(order.id)]]


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
async def test_janitor_terminal_probe_records_only_nonzero_partial_fill(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    filled_quantity: Decimal | None,
    expected_state: OrderState,
) -> None:
    order = await conditional_entry_factory(exchange_order_id="exchange-terminal")
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, _client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> OrderStatusFetch:
            assert trigger is True
            return OrderStatusFetch(
                exchange_order_id="exchange-terminal",
                status=status,  # type: ignore[arg-type]
                filled_price=Decimal("101") if filled_quantity else None,
                filled_quantity=filled_quantity,
                raw={},
            )

    _patch_task(monkeypatch, db_session, _Provider)

    await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert order.state == expected_state
    assert order.filled_quantity == (filled_quantity if filled_quantity else None)
    assert order.filled_price == (Decimal("101") if filled_quantity else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("probe_fails", [False, True])
async def test_janitor_keeps_form_two_when_probe_is_open_or_fails(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
    probe_fails: bool,
) -> None:
    order = await conditional_entry_factory(exchange_order_id="exchange-open")
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, _client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> OrderStatusFetch:
            assert trigger is True
            if probe_fails:
                raise RuntimeError("provider unavailable")
            return OrderStatusFetch(
                exchange_order_id="exchange-open",
                status="submitted",
                filled_price=None,
                filled_quantity=None,
                raw={},
            )

    dec, _ = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert result == {"repaired": 0, "rejected": 0, "terminal": 0}
    assert order.state == OrderState.submitted
    dec.assert_not_called()


@pytest.mark.asyncio
async def test_janitor_rejects_form_two_only_after_client_id_lookup_is_absent(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """form 2도 realtime+history 모두 비었을 때만 부재로 종결한다."""
    order = await conditional_entry_factory(exchange_order_id="exchange-ghost")
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> None:
            assert client_order_id == str(order.id)
            assert trigger is True
            return None

    dec, _ = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert result == {"repaired": 0, "rejected": 1, "terminal": 0}
    assert order.state == OrderState.rejected
    dec.assert_called_once()


@pytest.mark.asyncio
async def test_janitor_failure_does_not_stop_later_snapshot(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 rollback 뒤에도 같은 SELECT의 다음 행을 처리한다."""
    first = await conditional_entry_factory(
        exchange_order_id="exchange-first",
        submitted_at=datetime.now(UTC) - timedelta(minutes=32),
    )
    second = await conditional_entry_factory(
        exchange_order_id="exchange-second",
        submitted_at=datetime.now(UTC) - timedelta(minutes=31),
    )
    first_id, second_id = first.id, second.id
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> OrderStatusFetch:
            if client_order_id == str(first_id):
                raise RuntimeError("first probe fails")
            assert client_order_id == str(second_id)
            return OrderStatusFetch(
                exchange_order_id="exchange-second",
                status="filled",
                filled_price=Decimal("101"),
                filled_quantity=Decimal("0.001"),
                raw={},
            )

    dec, _ = _patch_task(monkeypatch, db_session, _Provider)
    metric = qb_live_conditional_reconcile_errors_total.labels(stage="janitor_probe")
    before = metric._value.get()

    result = await janitor_module._async_conditional_entry_janitor()
    first_after = await db_session.get(Order, first_id)
    second_after = await db_session.get(Order, second_id)

    assert result == {"repaired": 0, "rejected": 0, "terminal": 1}
    assert first_after is not None and first_after.state == OrderState.submitted
    assert second_after is not None and second_after.state == OrderState.filled
    assert metric._value.get() == before + 1
    dec.assert_called_once()


@pytest.mark.asyncio
async def test_conditional_janitor_metric_failure_does_not_escape_and_records_later_fill(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 probe의 라벨 mmap 실패 뒤에도 다음 조건부 진입은 체결로 종결한다."""
    first = await conditional_entry_factory(
        exchange_order_id="exchange-first",
        submitted_at=datetime.now(UTC) - timedelta(minutes=32),
    )
    second = await conditional_entry_factory(
        exchange_order_id="exchange-second",
        submitted_at=datetime.now(UTC) - timedelta(minutes=31),
    )
    first_id, second_id = first.id, second.id
    await db_session.commit()

    class _Provider:
        async def fetch_order_by_client_id(
            self, _creds: object, client_order_id: str, _symbol: str, *, trigger: bool = False
        ) -> OrderStatusFetch:
            if client_order_id == str(first_id):
                raise RuntimeError("first probe fails")
            assert client_order_id == str(second_id)
            return OrderStatusFetch(
                exchange_order_id="exchange-second",
                status="filled",
                filled_price=Decimal("101"),
                filled_quantity=Decimal("0.001"),
                raw={},
            )

    calls: list[str] = []

    def _explode_labels(*_args: object, **_kwargs: object) -> object:
        calls.append("labels")
        raise OSError("mmap allocation failed")

    monkeypatch.setattr(qb_live_conditional_reconcile_errors_total, "labels", _explode_labels)
    dec, _ = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    first_after = await db_session.get(Order, first_id)
    second_after = await db_session.get(Order, second_id)

    assert calls == ["labels"], "계측 라벨 생성 실패가 실제 보호 지점을 지나야 한다"
    assert result == {"repaired": 0, "rejected": 0, "terminal": 1}
    assert first_after is not None and first_after.state == OrderState.submitted
    assert second_after is not None and second_after.state == OrderState.filled
    dec.assert_called_once()


@pytest.mark.asyncio
async def test_janitor_ignores_conditional_entry_inside_cutoff(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = await conditional_entry_factory(
        exchange_order_id=None,
        submitted_at=datetime.now(UTC) - timedelta(minutes=29),
    )
    await db_session.commit()

    calls: list[tuple[object, ...]] = []

    class _Provider:
        async def fetch_order_by_client_id(self, *args: object, **kwargs: object) -> None:
            calls.append(args)
            return None

    dec, _ = _patch_task(monkeypatch, db_session, _Provider)

    result = await janitor_module._async_conditional_entry_janitor()
    await db_session.refresh(order)

    assert result == {"repaired": 0, "rejected": 0, "terminal": 0}
    assert order.state == OrderState.submitted
    assert calls == []
    dec.assert_not_called()

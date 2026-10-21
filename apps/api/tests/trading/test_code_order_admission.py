"""일반 신규 주문과 코드 venue의 동일 소유권 경계. DB는 슬롯, 거래소/큐는 대역이다."""

from decimal import Decimal as D
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.exceptions import CodePositionReserved
from src.trading.models import LiveRiskState, Order, OrderSide, OrderState, OrderType
from src.trading.providers import Credentials, OrderReceipt, OrderStatusFetch
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import OrderRequest
from src.trading.services.code_risk_service import (
    CodeRiskError,
    CodeRiskReconciliationPending,
    CodeRiskService,
)
from src.trading.services.code_risk_venue import BybitCodeRiskVenue
from src.trading.services.order_service import OrderService
from tests.trading import test_code_risk_repository as risk_tests
from tests.trading import test_code_symbol_admission as ownership_tests

prepared = risk_tests.prepared
scope = ownership_tests.scope


@pytest.mark.parametrize("allowed", [False, True])
@pytest.mark.parametrize("idempotency_key", [None, "manual-entry"])
@pytest.mark.parametrize("reduce_only", [False, True])
async def test_service_admission_follows_kill_switch_and_precedes_insert_commit(
    idempotency_key, reduce_only, allowed
):
    sql = AsyncMock(spec=AsyncSession)
    sql.begin_nested = MagicMock(return_value=AsyncMock())
    repo, gate, dispatcher = AsyncMock(), AsyncMock(), AsyncMock()
    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(1),
        reduce_only=reduce_only,
    )
    row = Order(**req.model_dump(exclude={"risk_percent"}), state=OrderState.pending)
    repo.save.return_value = repo.get_by_id.return_value = row
    repo.get_by_idempotency_key.return_value = None
    repo.has_unsettled_code_exit.return_value = False
    events = []
    gate.ensure_not_gated.side_effect = lambda **_: events.append("kill_switch")
    repo.acquire_entry_admission.side_effect = lambda *_: events.append("admission") or allowed
    repo.save.side_effect = lambda _: events.append("save") or row
    sql.commit.side_effect = lambda: events.append("commit")
    service = OrderService(sql, repo, dispatcher, gate)
    if reduce_only or allowed:
        await service.execute(req, idempotency_key=idempotency_key, body_hash=None)
        assert events == ["kill_switch", *([] if reduce_only else ["admission"]), "save", "commit"]
        if reduce_only:
            repo.acquire_entry_admission.assert_not_awaited()
        sql.commit.assert_awaited_once()
    else:
        with pytest.raises(CodePositionReserved):
            await service.execute(req, idempotency_key=idempotency_key, body_hash=None)
        assert events == ["kill_switch", "admission"]
        repo.save.assert_not_awaited()
        sql.commit.assert_not_awaited()
        dispatcher.dispatch_order_execution.assert_not_awaited()


@pytest.mark.parametrize("active", [True, False])
@pytest.mark.parametrize("uid,allowed", [("same-physical", False), (None, True)])
async def test_general_entry_wrapper_respects_active_and_unfinished_uid_siblings(
    db_session, scope, active, uid, allowed
):
    account, live, entry = scope
    owner_account, incoming_account = await account(uid), await account(uid)
    owner = await live(owner_account, active=active)
    if not active:
        parent = await entry(owner)
        db_session.add(
            LiveRiskState(
                session_id=owner.id,
                direction="long",
                entry_order_id=parent.id,
                expected_quantity=D(2),
                reference_bars=[],
                qty_step=D(".1"),
                min_qty=D(".1"),
                provisional_stop=D(90),
            )
        )
        await db_session.flush()
    assert (
        await OrderRepository(db_session).acquire_entry_admission(incoming_account.id, "BTCUSDT")
        is allowed
    )


async def test_generic_pending_order_blocks_later_code_but_not_legacy_registration(
    db_session, scope
):
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository

    account, live, _entry = scope
    acct = await account("physical")
    old = await live(acct, code=False, active=False)
    row = Order(
        strategy_id=old.strategy_id,
        exchange_account_id=acct.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(1),
        state=OrderState.pending,
    )
    repo = OrderRepository(db_session)
    assert await repo.acquire_entry_admission(acct.id, "BTCUSDT")
    await repo.save(row)
    await repo.commit()
    admission = LiveSignalSessionRepository(db_session)
    assert not await admission.acquire_code_symbol_admission(acct.id, "BTCUSDT", is_code=True)
    assert await admission.acquire_code_symbol_admission(acct.id, "BTCUSDT", is_code=False)


@pytest.mark.parametrize("reduce_only", [False, True])
async def test_venue_checks_admission_after_rules_before_submit_and_preserves_pending(
    prepared, db_session, reduce_only, monkeypatch
):
    repo, session, entry = prepared
    session.execution_snapshot = {"source_policy": "code_v1"}
    order = entry
    await db_session.refresh(entry)
    if reduce_only:
        order = Order(
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=D(1),
            state=OrderState.pending,
            reduce_only=True,
            risk_context={"session_id": str(session.id), "generation": 1, "role": "close"},
        )
        db_session.add(order)
    await db_session.commit()
    orders, provider = OrderRepository(db_session), AsyncMock()
    provider.fetch_order_by_client_id.return_value = None
    events = []
    provider.get_code_market_rules.side_effect = lambda *_: (
        events.append("rules") or {"price_tick": D(".1"), "qty_step": D(".1"), "min_qty": D(".1")}
    )
    admission = AsyncMock(side_effect=lambda _: events.append("admission") or False)
    monkeypatch.setattr(repo, "acquire_entry_admission", admission)
    commit = AsyncMock(wraps=repo.commit)
    monkeypatch.setattr(repo, "commit", commit)
    provider.create_order.return_value = OrderReceipt(
        exchange_order_id="fake-child", status="submitted", filled_price=None, raw={}
    )
    venue = BybitCodeRiskVenue(repo, orders, CodeRiskService(repo), AsyncMock(), provider)
    if reduce_only:
        await venue._submit(Credentials("fake", "fake"), order)
        admission.assert_not_awaited()
        assert provider.create_order.await_args.args[1].position_idx == 0
    else:
        with pytest.raises(CodeRiskReconciliationPending, match="소유권"):
            await venue._submit(Credentials("fake", "fake"), order)
        assert events == ["rules", "admission"]
        provider.create_order.assert_not_awaited()
        commit.assert_not_awaited()
        await db_session.refresh(order)
        assert order.state == OrderState.pending and order.submitted_at is None


@pytest.mark.parametrize("session_id", [None, "invalid", "00000000000000000000000000000000"])
async def test_new_code_entry_requires_canonical_session_uuid(prepared, db_session, session_id):
    repo, _session, entry = prepared
    await db_session.refresh(entry)
    entry.risk_context = {**entry.risk_context, "session_id": session_id}
    provider = AsyncMock()
    provider.fetch_order_by_client_id.return_value = None
    provider.get_code_market_rules.return_value = {
        "price_tick": D(".1"),
        "qty_step": D(".1"),
        "min_qty": D(".1"),
    }
    with pytest.raises(CodeRiskError, match="UUID"):
        await BybitCodeRiskVenue(
            repo, OrderRepository(db_session), CodeRiskService(repo), AsyncMock(), provider
        )._submit(Credentials("fake", "fake"), entry)
    provider.create_order.assert_not_awaited()


async def test_existing_exchange_order_skips_new_entry_admission(prepared, db_session, monkeypatch):
    repo, _session, entry = prepared
    await db_session.refresh(entry)
    provider = AsyncMock()
    provider.fetch_order_by_client_id.return_value = OrderStatusFetch(
        exchange_order_id="existing", status="submitted"
    )
    admission = AsyncMock(return_value=False)
    monkeypatch.setattr(repo, "acquire_entry_admission", admission)
    await BybitCodeRiskVenue(
        repo, OrderRepository(db_session), CodeRiskService(repo), AsyncMock(), provider
    )._submit(Credentials("fake", "fake"), entry)
    admission.assert_not_awaited()
    provider.create_order.assert_not_awaited()


@pytest.mark.parametrize("reduce_only", [False, True])
async def test_worker_final_admission_uses_physical_uid_scope_and_allows_reduction(
    db_session, scope, monkeypatch, reduce_only
):
    from contextlib import asynccontextmanager

    from src.tasks import trading
    from tests.tasks.test_exchange_order_response_metric import _Crypto

    account, live, _entry = scope
    owner_account, incoming = await account("physical"), await account(" physical ")
    owner = await live(owner_account)
    order = Order(
        strategy_id=owner.strategy_id,
        exchange_account_id=incoming.id,
        symbol="BTC/USDT",
        side=OrderSide.sell if reduce_only else OrderSide.buy,
        type=OrderType.market,
        quantity=D(1),
        state=OrderState.pending,
        reduce_only=reduce_only,
    )
    db_session.add(order)
    await db_session.commit()
    provider = AsyncMock()
    provider.create_order.return_value = OrderReceipt(
        exchange_order_id="mock-external", status="submitted", filled_price=None, raw={}
    )
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    monkeypatch.setattr(
        trading, "_provider_from_order_snapshot_or_fallback", lambda *_args, **_kwargs: provider
    )
    monkeypatch.setattr(trading, "publish_realtime", AsyncMock())
    monkeypatch.setattr(trading.fetch_order_status_task, "apply_async", MagicMock())

    @asynccontextmanager
    async def sm():
        yield db_session

    result = await trading._execute_with_session(order.id, sm)
    await db_session.refresh(order)
    if reduce_only:
        provider.create_order.assert_awaited_once()
        assert order.state == OrderState.submitted
    else:
        assert result["error_message"] == "code_position_reserved"
        provider.create_order.assert_not_awaited()
        assert order.state == OrderState.rejected


@pytest.mark.parametrize("allowed", [False, True])
async def test_worker_rechecks_after_provider_selection_and_releases_lock_before_io(
    monkeypatch, allowed
):
    from src.tasks import trading
    from tests.tasks.test_exchange_order_response_metric import (
        _patch_execution,
        _receipt,
        _SessionContext,
    )

    harness, sql = _patch_execution(monkeypatch, _receipt("submitted"))
    events = []
    harness.repo.acquire_entry_admission = AsyncMock(
        side_effect=lambda *_: events.append("admission") or allowed
    )
    sql.commit.side_effect = lambda: events.append("commit")

    def selected(*_args, **_kwargs):
        events.append("provider_selected")
        return harness.provider

    monkeypatch.setattr(trading, "_provider_from_order_snapshot_or_fallback", selected)
    original = harness.provider.create_order.return_value
    harness.provider.create_order.side_effect = lambda *_: events.append("create") or original
    result = await trading._execute_with_session(harness.order.id, lambda: _SessionContext(sql))
    harness.repo.acquire_entry_admission.assert_awaited_once_with(
        harness.order.exchange_account_id, harness.order.symbol
    )
    assert events.index("provider_selected") < events.index("admission")
    if allowed:
        assert events[events.index("admission") :][:3] == ["admission", "commit", "create"]
        harness.provider.create_order.assert_awaited_once()
    else:
        assert result["error_message"] == "code_position_reserved"
        harness.provider.create_order.assert_not_awaited()


async def test_code_entry_final_admission_commits_reservation_before_oneway_submit(
    prepared, db_session, monkeypatch
):
    repo, session, entry = prepared
    await db_session.refresh(entry)
    session.symbol = entry.symbol = "BTC/USDT"
    session.execution_snapshot = {"source_policy": "code_v1"}
    await db_session.commit()
    events = []
    admission = repo.acquire_entry_admission

    async def check(identifier):
        events.append("admission")
        return await admission(identifier)

    monkeypatch.setattr(repo, "acquire_entry_admission", AsyncMock(side_effect=check))
    commit = repo.commit

    async def committing():
        events.append("commit")
        await commit()

    monkeypatch.setattr(repo, "commit", AsyncMock(side_effect=committing))
    provider = AsyncMock()
    provider.fetch_order_by_client_id.return_value = None
    provider.get_code_market_rules.return_value = {
        "price_tick": D(".1"),
        "qty_step": D(".1"),
        "min_qty": D(".1"),
    }

    async def submitted(_credentials, request):
        events.append("create")
        assert request.position_idx == 0
        await db_session.refresh(entry)
        assert entry.state == OrderState.submitted
        return OrderReceipt(
            exchange_order_id="oneway-entry", status="submitted", filled_price=None, raw={}
        )

    provider.create_order.side_effect = submitted
    await BybitCodeRiskVenue(
        repo, OrderRepository(db_session), CodeRiskService(repo), AsyncMock(), provider
    )._submit(Credentials("fake", "fake"), entry)
    assert events[:3] == ["admission", "commit", "create"]
    repo.acquire_entry_admission.assert_awaited_once_with(session.id)


async def test_actual_order_service_cannot_store_manual_entry_under_code_owner(
    db_session, scope, monkeypatch
):
    account, live, _entry = scope
    owner_account, incoming = await account("physical"), await account("physical")
    owner = await live(owner_account)
    repo, dispatcher = OrderRepository(db_session), AsyncMock()
    commit = AsyncMock(wraps=db_session.commit)
    monkeypatch.setattr(db_session, "commit", commit)
    req = OrderRequest(
        strategy_id=owner.strategy_id,
        exchange_account_id=incoming.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(1),
    )
    with pytest.raises(CodePositionReserved):
        await OrderService(db_session, repo, dispatcher, AsyncMock()).execute(
            req, idempotency_key=None, body_hash=None
        )
    commit.assert_not_awaited()
    dispatcher.dispatch_order_execution.assert_not_awaited()

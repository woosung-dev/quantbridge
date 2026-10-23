"""단일 거래소 관측의 제한 지원과 legacy 합산 경계를 fake V5·슬롯 SQL로 검증한다."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal as D
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.models import (
    ExchangeExit,
    ExitAttribution,
    ExitClassification,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import (
    _CLOSED_PNL_MAX_PAGES,
    BybitFuturesProvider,
    ClosedPnlSnapshot,
    CodeClosedPnlEvidence,
    CodeClosedPnlRead,
    Credentials,
    aggregate_closed_pnl_by_order,
    closed_pnl_raw_hash,
)
from src.trading.repositories.order_repository import OrderRepository, SessionScope
from tests.trading import test_code_risk_repository as risk_tests

prepared = risk_tests.prepared


def raw(**extra):
    return {
        "orderId": "exit",
        "symbol": "BTCUSDT",
        "side": "Sell",
        "execType": "Trade",
        "closedSize": "0.3",
        "closedPnl": "-1.25",
        "fillCount": "4",
        "updatedTime": "10",
        **extra,
    }


def page(rows, cursor=""):
    return {"retCode": 0, "result": {"category": "linear", "list": rows, "nextPageCursor": cursor}}


@pytest.fixture
def exchange(monkeypatch):
    exchange = MagicMock()
    exchange.privateGetV5PositionClosedPnl = AsyncMock()
    exchange.close = AsyncMock()
    monkeypatch.setattr("src.trading.providers.ccxt_async.bybit", lambda _: exchange)
    return exchange


async def read(exchange):
    return await BybitFuturesProvider().fetch_code_closed_pnl(
        Credentials("fake", "fake"),
        account_id=uuid4(),
        order_id="exit",
        symbol="BTC/USDT",
        side=OrderSide.sell,
        since=datetime.now(UTC),
    )


async def test_exact_raw_duplicates_across_complete_cursor_pages_are_one_observation(exchange):
    exchange.privateGetV5PositionClosedPnl.side_effect = [
        page([raw()], "next"),
        page([dict(reversed(list(raw().items())))]),
    ]
    result = await read(exchange)
    assert result.evidence.quantity == D(".3") and result.evidence.pnl == D("-1.25")
    assert not result.conflict and len(result.observed_hashes) == 1
    calls = exchange.privateGetV5PositionClosedPnl.await_args_list
    assert calls[0].args[0]["limit"] == 100 and calls[1].args[0]["cursor"] == "next"
    assert "orderId" not in calls[0].args[0]
    exchange.close.assert_awaited_once()


@pytest.mark.parametrize(
    "changes", [{"closedSize": ".1"}, {"updatedTime": "11"}, {"closedPnl": "-2"}]
)
async def test_different_snapshot_is_unknown_even_when_quantities_could_compensate(
    exchange, changes
):
    exchange.privateGetV5PositionClosedPnl.return_value = page([raw(), raw(**changes)])
    result = await read(exchange)
    assert result.evidence is None and result.conflict and len(result.observed_hashes) == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"closedSize": None},
        {"closedSize": "bad"},
        {"closedSize": "-1"},
        {"closedSize": "NaN"},
        {"closedSize": "Infinity"},
        {"closedPnl": None},
        {"closedPnl": "NaN"},
        {"side": "Buy"},
        {"execType": "BustTrade"},
        {"symbol": "ETHUSDT"},
    ],
)
async def test_inappropriate_matching_row_is_positive_conflict(exchange, changes):
    exchange.privateGetV5PositionClosedPnl.return_value = page([raw(**changes)])
    result = await read(exchange)
    assert result.evidence is None and result.conflict


@pytest.mark.parametrize("cursor", [None, [], 0])
async def test_incomplete_cursor_never_proves_a_single_observation(exchange, cursor):
    exchange.privateGetV5PositionClosedPnl.return_value = page([raw()], cursor)
    result = await read(exchange)
    assert result.evidence is None and not result.conflict


async def test_budget_and_repeated_cursor_are_unknown_without_relabeling_single_row_as_conflict(
    exchange,
):
    exchange.privateGetV5PositionClosedPnl.side_effect = [
        page([raw()], str(n)) for n in range(_CLOSED_PNL_MAX_PAGES)
    ]
    result = await read(exchange)
    assert result.evidence is None and not result.conflict
    assert exchange.privateGetV5PositionClosedPnl.await_count == _CLOSED_PNL_MAX_PAGES
    exchange.privateGetV5PositionClosedPnl.side_effect = [
        page([raw()], "same"),
        page([raw()], "same"),
    ]
    result = await read(exchange)
    assert result.evidence is None and not result.conflict


def test_legacy_aggregate_deduplicates_only_identical_raw_and_preserves_none_and_distinct_rows():
    first = ClosedPnlSnapshot("exit", D(1), D(".1"), None, 1, raw=raw())
    changed = replace(first, closed_pnl=D(2), closed_size=D(".2"), raw=raw(updatedTime="11"))
    result = aggregate_closed_pnl_by_order([first, first, changed])["exit"]
    assert result.closed_pnl == 3 and result.closed_size == D(".3")
    none = replace(first, raw=None)
    assert aggregate_closed_pnl_by_order([none, none])["exit"].closed_pnl == 2


@pytest.fixture
async def exit_order(prepared, db_session):
    _risk_repo, live, _parent = prepared
    live.execution_snapshot = {"source_policy": "code_v1"}
    order = Order(
        strategy_id=live.strategy_id,
        exchange_account_id=live.exchange_account_id,
        symbol=live.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(1),
        filled_quantity=D(".3"),
        filled_price=D(100),
        filled_at=datetime.now(UTC),
        state=OrderState.cancelled,
        reduce_only=True,
        leverage=1,
        exchange_order_id="exit",
        risk_context={"session_id": str(live.id), "generation": 1, "role": "partial_tp"},
    )
    db_session.add(order)
    await db_session.commit()
    evidence = CodeClosedPnlEvidence(
        order.exchange_account_id,
        "exit",
        "BTCUSDT",
        OrderSide.sell,
        D(".3"),
        D("-1.25"),
        closed_pnl_raw_hash(raw()),
    )
    return OrderRepository(db_session), live, order, evidence


@pytest.mark.parametrize(
    "change",
    [
        None,
        {"quantity": D(".1")},
        {"quantity": D("NaN")},
        {"account_id": uuid4()},
        {"order_id": "foreign"},
        {"side": OrderSide.buy},
    ],
)
async def test_repository_cas_fails_closed_without_matching_terminal_quantity_and_scope(
    exit_order, db_session, change
):
    repo, _live, order, evidence = exit_order
    supplied = None if change is None else replace(evidence, **change)
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=supplied
        )
        == 0
    )
    await db_session.refresh(order)
    assert order.realized_pnl is None and order.realized_pnl_synced_at is None


async def test_matched_fractional_quantity_applies_once_and_entry_never_confirms(
    exit_order, db_session
):
    repo, _live, order, evidence = exit_order
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 1
    )
    await repo.commit()
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 0
    )
    order.reduce_only = False
    order.risk_context = {**order.risk_context, "role": "entry"}
    order.realized_pnl = order.realized_pnl_synced_at = None
    await repo.commit()
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 0
    )


async def test_different_ledger_snapshot_is_durable_incomplete_and_cannot_be_cleared_by_single_read(
    exit_order, db_session
):
    repo, live, order, evidence = exit_order
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 1
    )
    await repo.commit()
    old_synced = order.realized_pnl_synced_at
    conflicting = raw(updatedTime="11")
    db_session.add(
        ExchangeExit(
            exchange_account_id=order.exchange_account_id,
            exchange_order_id="exit",
            row_hash=uuid4().hex,
            symbol="BTCUSDT",
            side="Sell",
            closed_pnl=evidence.pnl,
            closed_size=D(".3"),
            exchange_created_at=datetime.now(UTC),
            classification=ExitClassification.ours,
            attribution_confidence=ExitAttribution.exact,
            raw=conflicting,
        )
    )
    await repo.commit()
    assert (
        await repo.resync_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 0
    )
    await repo.commit()
    assert (
        await repo.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(live)) == 1
    )
    await db_session.refresh(order)
    assert order.realized_pnl == evidence.pnl and order.realized_pnl_synced_at == old_synced
    assert len(order.risk_context["pnl_evidence_conflict"]["raw_hashes"]) == 2
    assert (
        await repo.resync_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 0
    )
    assert (
        await repo.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(live)) == 1
    )


@pytest.mark.parametrize("matched", [True, False])
async def test_actual_refresh_code_path_uses_complete_evidence_and_commits(
    exit_order, db_session, monkeypatch, matched
):
    from contextlib import asynccontextmanager

    from src.tasks import trading
    from tests.tasks.test_exchange_order_response_metric import _Crypto

    _repo, _live, order, evidence = exit_order
    provider = AsyncMock()
    provider.fetch_code_closed_pnl.return_value = CodeClosedPnlRead(evidence if matched else None)
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    commit = AsyncMock(wraps=db_session.commit)
    monkeypatch.setattr(db_session, "commit", commit)

    @asynccontextmanager
    async def sm():
        yield db_session

    result = await trading._refresh_closed_pnl_with_session(order.id, sm, provider=provider)
    provider.fetch_code_closed_pnl.assert_awaited_once()
    provider.fetch_closed_pnl.assert_not_awaited()
    commit.assert_awaited_once()
    await db_session.refresh(order)
    assert order.realized_pnl == (evidence.pnl if matched else None)
    assert ("applied" in result) is matched


@pytest.mark.parametrize("consistent", [False, True])
async def test_actual_sweep_cannot_promote_legacy_aggregate_into_code_pnl(
    exit_order, db_session, monkeypatch, consistent
):
    from contextlib import asynccontextmanager

    from src.tasks import trading
    from tests.tasks.test_exchange_order_response_metric import _Crypto

    _repo, _live, order, evidence = exit_order
    provider = AsyncMock()
    snapshot = ClosedPnlSnapshot(
        "exit",
        D(99),
        D(".1"),
        D(100),
        1,
        symbol="BTCUSDT",
        side="Sell",
        created_at_ms=int(datetime.now(UTC).timestamp() * 1000),
        raw=raw(closedSize=".1", closedPnl="99"),
    )
    if consistent:
        snapshot = replace(
            snapshot, closed_pnl=evidence.pnl, closed_size=evidence.quantity, raw=raw()
        )
    provider.fetch_closed_pnl_window.return_value = [snapshot, snapshot]
    provider.fetch_code_closed_pnl.return_value = CodeClosedPnlRead(evidence)
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    monkeypatch.setattr(trading, "_alert_new_exchange_exits", AsyncMock(return_value=False))

    @asynccontextmanager
    async def sm():
        yield db_session

    summary = await trading._sweep_closed_pnl_with_session(sm, provider=provider)
    await db_session.refresh(order)
    # 이미 원장에 다른 raw가 있으므로 strict read 단일 값도 충돌을 지우지 못한다.
    assert order.realized_pnl == (evidence.pnl if consistent else None)
    assert summary["backfilled"] == int(consistent)
    assert bool(order.risk_context.get("pnl_evidence_conflict")) is not consistent
    # 첫 원장 관측만으로 충돌이 성립하지 않는다. 최초 strict 조회의 다른 raw와 대조한다.
    provider.fetch_code_closed_pnl.assert_awaited_once()


@pytest.mark.parametrize(
    "later",
    [
        page([raw(orderId="foreign", symbol="ETHUSDT")]),
        {"retCode": 0, "result": None},
        page([None]),
        TimeoutError("network"),
    ],
)
async def test_known_positive_conflict_survives_later_failed_page(exchange, later):
    exchange.privateGetV5PositionClosedPnl.side_effect = [
        page([raw(), raw(updatedTime="11")], "next"),
        later,
    ]
    result = await read(exchange)
    assert result.evidence is None and result.conflict and len(result.observed_hashes) == 2


async def test_foreign_malformed_symbol_is_not_target_observation(exchange):
    exchange.privateGetV5PositionClosedPnl.return_value = page(
        [raw(orderId="foreign", symbol="ETHUSDT")]
    )
    result = await read(exchange)
    assert result.evidence is None and not result.conflict and result.observed_hashes == ()


@pytest.mark.parametrize(
    "response",
    [
        page([]),
        {"retCode": 1, "result": None},
        {"retCode": 0, "result": {"category": "spot", "list": [], "nextPageCursor": ""}},
        page([raw()] * 101),
    ],
)
async def test_empty_wrong_scope_and_oversized_pages_cannot_authorize_code_pnl(exchange, response):
    exchange.privateGetV5PositionClosedPnl.return_value = response
    result = await read(exchange)
    assert result.evidence is None and not result.conflict


async def test_single_observation_then_transport_failure_is_retry_not_conflict(exchange):

    exchange.privateGetV5PositionClosedPnl.side_effect = [
        page([raw()], "next"),
        TimeoutError("network"),
    ]
    observed = await read(exchange)
    assert observed.evidence is None and not observed.conflict
    assert len(observed.observed_hashes) == 1


async def test_query_unavailable_preserves_old_observation_and_completeness(exit_order, exchange):
    repo, live, order, evidence = exit_order
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 1
    )
    await repo.commit()
    exchange.privateGetV5PositionClosedPnl.return_value = page(
        [raw(orderId="foreign", symbol="ETHUSDT")]
    )
    observed = await read(exchange)
    assert not await repo.mark_code_pnl_conflict(
        order.id, observed.observed_hashes, invalid=observed.conflict
    )
    await repo.commit()
    assert order.realized_pnl == evidence.pnl
    assert (
        await repo.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(live)) == 0
    )


async def test_existing_same_amount_keeps_timestamp_and_records_first_matching_proof(
    exit_order, db_session
):
    repo, live, order, evidence = exit_order
    order.realized_pnl, order.realized_pnl_synced_at = evidence.pnl, datetime.now(UTC)
    await repo.commit()
    previous_time = order.realized_pnl_synced_at
    assert (
        await repo.resync_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 0
    )
    await repo.commit()
    await db_session.refresh(order)
    assert order.risk_context["code_pnl_evidence"]["raw_hash"] == evidence.raw_hash
    assert order.realized_pnl_synced_at == previous_time
    changed = replace(evidence, raw_hash=closed_pnl_raw_hash(raw(updatedTime="11")))
    assert (
        await repo.resync_exchange_realized_pnl(
            order.id, realized_pnl=changed.pnl, synced_at=datetime.now(UTC), code_evidence=changed
        )
        == 0
    )
    await repo.commit()
    assert (
        await repo.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(live)) == 1
    )
    assert order.realized_pnl == evidence.pnl and order.realized_pnl_synced_at == previous_time


async def test_foreign_envelope_cannot_poison_existing_proof(exit_order):
    repo, live, order, evidence = exit_order
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 1
    )
    await repo.commit()
    foreign = replace(evidence, account_id=uuid4(), raw_hash="foreign")
    assert (
        await repo.resync_exchange_realized_pnl(
            order.id, realized_pnl=foreign.pnl, synced_at=datetime.now(UTC), code_evidence=foreign
        )
        == 0
    )
    await repo.commit()
    assert (
        await repo.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(live)) == 0
    )


async def test_actual_sweep_marks_same_amount_new_raw_without_resync_starvation(
    exit_order, db_session, monkeypatch
):
    from contextlib import asynccontextmanager

    from src.tasks import trading
    from tests.tasks.test_exchange_order_response_metric import _Crypto

    repo, live, order, evidence = exit_order
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=evidence.pnl, synced_at=datetime.now(UTC), code_evidence=evidence
        )
        == 1
    )
    await repo.commit()
    old_time = order.realized_pnl_synced_at
    provider = AsyncMock()
    provider.fetch_closed_pnl_window.return_value = [
        ClosedPnlSnapshot(
            "exit",
            evidence.pnl,
            evidence.quantity,
            D(100),
            11,
            symbol="BTCUSDT",
            side="Sell",
            created_at_ms=int(datetime.now(UTC).timestamp() * 1000),
            raw=raw(updatedTime="11"),
        )
    ]
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    monkeypatch.setattr(trading, "_alert_new_exchange_exits", AsyncMock(return_value=False))

    @asynccontextmanager
    async def sm():
        yield db_session

    await trading._sweep_closed_pnl_with_session(sm, provider=provider)
    await db_session.refresh(order)
    assert order.realized_pnl == evidence.pnl and order.realized_pnl_synced_at == old_time
    assert (
        await repo.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(live)) == 1
    )
    assert order.risk_context["pnl_evidence_conflict"]
    provider.fetch_code_closed_pnl.assert_not_awaited()


async def test_cleanup_failure_does_not_discard_complete_observation(exchange):
    exchange.privateGetV5PositionClosedPnl.return_value = page([raw()])
    exchange.close.side_effect = RuntimeError("cleanup")
    observed = await read(exchange)
    assert observed.evidence is not None and not observed.conflict


async def test_later_order_transport_error_does_not_discard_prior_order_conflict(
    exit_order, db_session, monkeypatch
):
    from contextlib import asynccontextmanager
    from datetime import timedelta

    from src.tasks import trading
    from src.trading.exceptions import ProviderError
    from tests.tasks.test_exchange_order_response_metric import _Crypto

    _repo, _live, first, _evidence = exit_order
    second = Order(
        **{
            **first.model_dump(),
            "id": uuid4(),
            "exchange_order_id": "second",
            "filled_at": first.filled_at + timedelta(seconds=1),
        }
    )
    db_session.add(second)
    await db_session.commit()
    provider = AsyncMock()
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    provider.fetch_closed_pnl_window.return_value = [
        ClosedPnlSnapshot(
            identifier,
            D("-1.25"),
            D(".3"),
            D(100),
            10,
            symbol="BTCUSDT",
            side="Sell",
            created_at_ms=now_ms,
            raw=raw(orderId=identifier),
        )
        for identifier in ("exit", "second")
    ]
    provider.fetch_code_closed_pnl.side_effect = [
        CodeClosedPnlRead(
            None, (closed_pnl_raw_hash(raw()), closed_pnl_raw_hash(raw(updatedTime="11"))), True
        ),
        ProviderError("timeout"),
    ]
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    monkeypatch.setattr(trading, "_alert_new_exchange_exits", AsyncMock(return_value=False))

    @asynccontextmanager
    async def sm():
        yield db_session

    await trading._sweep_closed_pnl_with_session(sm, provider=provider)
    await db_session.refresh(first)
    assert first.risk_context["pnl_evidence_conflict"]
    assert first.realized_pnl is None and second.realized_pnl is None

# 조건부 진입 reconcile의 거래소 배선과 귀속 불변식을 검증한다.
from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]

from src.strategy.pine_v2.event_loop import PendingOrderSnapshot  # noqa: E402
from src.strategy.schemas import StrategySettings  # noqa: E402
from src.trading.models import OrderSide, OrderState  # noqa: E402
from src.trading.providers import ConditionalOrderSnapshot, PositionSnapshot  # noqa: E402
from src.trading.services.conditional_entry_planner import (  # noqa: E402
    build_conditional_entry_key,
    build_market_converted_entry_key,
    parse_conditional_entry_key,
)


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


_BAR_TIME = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _session() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval="1m",
        is_active=True,
    )


def _pending(trade_id: str = "entry") -> PendingOrderSnapshot:
    return PendingOrderSnapshot(
        trade_id=trade_id,
        direction="long",
        target_position=Decimal("1"),
        entry_qty=Decimal("1"),
        stop_price=Decimal("100"),
        placed_bar=1,
        comment="entry",
    )


def _result(pending_orders: list[PendingOrderSnapshot]) -> SimpleNamespace:
    return SimpleNamespace(pending_orders=pending_orders)


def _order(
    session: SimpleNamespace,
    *,
    trade_id: str = "entry",
    strategy_id: UUID | None = None,
    exchange_account_id: UUID | None = None,
    exchange_order_id: str | None = None,
    submitted_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        strategy_id=strategy_id or session.strategy_id,
        exchange_account_id=exchange_account_id or session.exchange_account_id,
        trigger_price=Decimal("100"),
        quantity=Decimal("1"),
        side=OrderSide.buy,
        trigger_direction=1,
        reduce_only=False,
        state=OrderState.submitted,
        exchange_order_id=exchange_order_id,
        # BL-500 나이 게이트 기본값 = "방금 제출" — 게이트가 열리려면 테스트가 명시적으로
        # 늙혀야 한다. 기본이 늙은 값이면 무관한 테스트가 조용히 제거 경로를 탄다.
        submitted_at=submitted_at if submitted_at is not None else datetime.now(UTC),
        idempotency_key=build_conditional_entry_key(
            session.id, trade_id, _BAR_TIME, Decimal("100"), Decimal("1")
        ),
    )


def _exchange_order(order: SimpleNamespace) -> ConditionalOrderSnapshot:
    return ConditionalOrderSnapshot(
        order_id=order.exchange_order_id or "exchange-entry",
        side="buy",
        kind="other",
        price=None,
        trigger_price=Decimal("100"),
        qty=Decimal("1"),
        reduce_only=False,
        position_idx=0,
        order_link_id=str(order.id),
    )


def _patch_reconcile(
    monkeypatch: pytest.MonkeyPatch,
    *,
    local_orders: list[SimpleNamespace] | None = None,
    exchange_orders: list[ConditionalOrderSnapshot] | None = None,
    positions: list[PositionSnapshot] | None = None,
    database_orders: list[SimpleNamespace] | None = None,
    precision_error: Exception | None = None,
    execute_error: Exception | None = None,
    active_sessions: list[SimpleNamespace] | None = None,
    pending_cancel_rows: int = 1,
    fresh_state: OrderState | None = OrderState.submitted,
    fresh_exchange_order_id: str | None = "exchange-raced",
    exchange_orders_error: Exception | None = None,
    probe_status: str | None = "submitted",
    probe_error: Exception | None = None,
    last_price: Decimal | None = Decimal("64"),
    recent_market_conversion: bool = False,
) -> SimpleNamespace:
    session = AsyncMock()
    order_repo = AsyncMock()
    order_repo.list_resting_conditional_entries = AsyncMock(return_value=local_orders or [])
    orders_by_id = {order.id: order for order in database_orders or local_orders or []}

    async def get_by_id(order_id: UUID) -> SimpleNamespace | None:
        return orders_by_id.get(order_id)

    order_repo.get_by_id = AsyncMock(side_effect=get_by_id)
    order_repo.transition_to_cancelled = AsyncMock(return_value=1)
    order_repo.transition_pending_to_cancelled = AsyncMock(return_value=pending_cancel_rows)
    order_repo.get_state_and_exchange_id_fresh = AsyncMock(
        return_value=None if fresh_state is None else (fresh_state, fresh_exchange_order_id)
    )
    order_repo.has_recent_market_converted_entry = AsyncMock(return_value=recent_market_conversion)
    order_repo.commit = AsyncMock()

    account_repo = AsyncMock()
    kill_switch_repo = AsyncMock()
    kill_switch_repo.get_active = AsyncMock(return_value=None)

    # 같은 계정·심볼의 다른 활성 세션 = 계정 순포지션이 우리 것만이 아니라는 신호.
    live_session_repo = AsyncMock()
    live_session_repo.list_active_by_account = AsyncMock(return_value=active_sessions or [])

    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.kill_switch_event_repository as kill_switch_repo_module
    import src.trading.repositories.live_signal_session_repository as live_session_repo_module
    import src.trading.repositories.order_repository as order_repo_module

    monkeypatch.setattr(
        live_session_repo_module,
        "LiveSignalSessionRepository",
        MagicMock(return_value=live_session_repo),
    )
    monkeypatch.setattr(order_repo_module, "OrderRepository", MagicMock(return_value=order_repo))
    monkeypatch.setattr(
        account_repo_module, "ExchangeAccountRepository", MagicMock(return_value=account_repo)
    )
    monkeypatch.setattr(
        kill_switch_repo_module,
        "KillSwitchEventRepository",
        MagicMock(return_value=kill_switch_repo),
    )

    provider = AsyncMock()
    provider.fetch_open_conditional_orders = AsyncMock(
        return_value=exchange_orders or [], side_effect=exchange_orders_error
    )
    provider.fetch_open_positions = AsyncMock(return_value=positions or [])
    provider.fetch_last_price = AsyncMock(return_value=last_price)
    provider.cancel_order = AsyncMock()
    provider.fetch_order = AsyncMock(
        return_value=SimpleNamespace(
            exchange_order_id="probe",
            status=probe_status,
            filled_price=None,
            filled_quantity=None,
            raw={},
        ),
        side_effect=probe_error,
    )

    import src.trading.providers as providers_module

    monkeypatch.setattr(providers_module, "BybitFuturesProvider", MagicMock(return_value=provider))

    exchange_service = AsyncMock()
    exchange_service.get_credentials_for_order = AsyncMock(return_value=SimpleNamespace())
    import src.trading.services.account_service as account_service_module

    monkeypatch.setattr(
        account_service_module, "ExchangeAccountService", MagicMock(return_value=exchange_service)
    )

    order_service = AsyncMock()
    if execute_error is None:
        order_service.execute = AsyncMock(return_value=(SimpleNamespace(id=uuid4()), False))
    else:
        order_service.execute = AsyncMock(side_effect=execute_error)
    import src.trading.services.order_service as order_service_module

    monkeypatch.setattr(order_service_module, "OrderService", MagicMock(return_value=order_service))

    market_exchange = SimpleNamespace(
        load_markets=AsyncMock(side_effect=precision_error),
        market=MagicMock(return_value={"precision": {"amount": "0.001", "price": "0.1"}}),
    )
    monkeypatch.setattr(
        celery_module,
        "get_ccxt_provider_for_worker",
        lambda: SimpleNamespace(exchange=market_exchange),
    )

    return SimpleNamespace(
        order_repo=order_repo,
        provider=provider,
        order_service=order_service,
        market_exchange=market_exchange,
        sm=lambda: _SessionContext(session),
    )


async def _reconcile(
    session: SimpleNamespace,
    result: SimpleNamespace,
    harness: SimpleNamespace,
    *,
    market_orders_in_flight: bool = False,
    fallback_reference_price: Decimal | None = None,
    max_trigger_breach_pct: float | None = None,
) -> None:
    await live_signal_module._reconcile_conditional_entries(
        session,
        result,
        StrategySettings(
            leverage=2,
            margin_mode="cross",
            position_size_pct=10,
            max_trigger_breach_pct=max_trigger_breach_pct,
        ),
        harness.sm,
        bar_time=_BAR_TIME,
        market_orders_in_flight=market_orders_in_flight,
        fallback_reference_price=fallback_reference_price,
    )


def test_conditional_key_round_trip_preserves_colon_in_trade_id() -> None:
    session_id = uuid4()

    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    epoch = int(bar_time.timestamp())

    key = build_conditional_entry_key(
        session_id, "entry:leg:one", bar_time, Decimal("100"), Decimal("1")
    )

    assert key == f"live:{session_id}:cond:{epoch}:100:1:entry:leg:one"
    assert parse_conditional_entry_key(key) == (session_id, "entry:leg:one")


def test_conditional_key_changes_per_bar_so_replacement_actually_dispatches() -> None:
    """★같은 의도라도 bar 가 다르면 key 가 달라야 한다.

    key 가 (trade_id, 가격, 수량) 만으로 결정되면 취소 후 재등재 때 OrderService 가
    dispatch 없이 캐시 응답을 돌려준다 - 거래소엔 아무것도 없는데 DB 와 metric 은
    "등재됨" 이라고 보고한다.
    """
    session_id = uuid4()
    args = ("PivRevLE", Decimal("100"), Decimal("1"))
    first = build_conditional_entry_key(
        session_id, args[0], datetime(2026, 5, 1, 12, 0, tzinfo=UTC), *args[1:]
    )
    second = build_conditional_entry_key(
        session_id, args[0], datetime(2026, 5, 1, 13, 0, tzinfo=UTC), *args[1:]
    )

    assert first != second
    assert parse_conditional_entry_key(first) == parse_conditional_entry_key(second)


def test_conditional_key_rejects_unrepresentable_trade_ids() -> None:
    """빈 trade_id 와 200자 초과는 발주하면 안 된다.

    전자는 파서가 되짚지 못해 우리 주문을 영원히 남의 것으로 보게 만들고,
    후자는 VARCHAR(200) 오류가 상위 except 에 삼켜져 "장전됐다고 믿는데 거래소엔 없는"
    상태를 만든다.
    """
    session_id = uuid4()
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    assert (
        build_conditional_entry_key(session_id, "  ", bar_time, Decimal("1"), Decimal("1")) is None
    )
    assert (
        build_conditional_entry_key(session_id, "x" * 200, bar_time, Decimal("1"), Decimal("1"))
        is None
    )


@pytest.mark.asyncio
async def test_zero_cost_shortcut_skips_exchange_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([]), harness)

    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.provider.fetch_last_price.assert_not_awaited()


@pytest.mark.asyncio
async def test_reference_price_comes_from_exchange_last_not_bar_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price is None
    assert harness.provider.fetch_last_price.await_count == 2
    harness.provider.fetch_last_price.assert_awaited_with(ANY, session.symbol)


@pytest.mark.asyncio
async def test_reference_price_not_fetched_when_no_conditional_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([]), harness)

    harness.provider.fetch_last_price.assert_not_awaited()


@pytest.mark.asyncio
async def test_reference_price_failure_still_places_conditional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id="exchange-old")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        exchange_orders=[_exchange_order(stale)],
        last_price=None,
    )

    await _reconcile(
        session,
        _result([_pending("new")]),
        harness,
        fallback_reference_price=Decimal("99"),
    )

    harness.provider.fetch_last_price.assert_awaited_once_with(ANY, session.symbol)
    harness.provider.cancel_order.assert_awaited_once_with(ANY, "exchange-old", session.symbol)
    harness.order_service.execute.assert_awaited_once()
    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price == Decimal("100")


@pytest.mark.asyncio
async def test_reference_price_failure_forbids_market_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=None)

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        fallback_reference_price=Decimal("110"),
    )

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_reference_forbids_conversion_even_if_reprobe_would_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★평가자 추가 게이트 - 전환 금지의 주체가 폴백 판정임을 분리해 고정한다.

    첫 조회 실패와 발주 직전 재확인이 같은 대역을 쓰면 둘 다 None 이라 어느 가드가
    막았는지 구분되지 않는다(변이 F7 이 그 틈으로 통과했다). 첫 조회만 실패시키고
    재확인은 성공시키면 폴백 판정만 남는다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=None)
    harness.provider.fetch_last_price = AsyncMock(side_effect=[None, Decimal("110")])

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        fallback_reference_price=Decimal("110"),
    )

    assert harness.provider.fetch_last_price.await_count == 1
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejected_recent_conversion_still_suppresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        last_price=Decimal("110"),
        recent_market_conversion=True,
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_repo.has_recent_market_converted_entry.assert_awaited_once()
    harness.order_service.execute.assert_not_awaited()
    harness.provider.fetch_last_price.assert_awaited_once_with(ANY, session.symbol)


@pytest.mark.asyncio
async def test_breach_reverted_before_place_skips_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    harness.provider.fetch_last_price.side_effect = [Decimal("110"), Decimal("99")]

    await _reconcile(session, _result([_pending()]), harness)

    assert harness.provider.fetch_last_price.await_count == 2
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_breach_exceeding_cap_at_reprobe_is_not_converted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.common.metrics import qb_live_conditional_guard_total

    cap = Decimal("1")
    initial_reference_price = Decimal("100.5")
    reprobe_reference_price = Decimal("102")
    initial_breach_pct = (
        abs(initial_reference_price - Decimal("100")) / initial_reference_price * Decimal("100")
    )
    reprobe_breach_pct = (
        abs(reprobe_reference_price - Decimal("100")) / reprobe_reference_price * Decimal("100")
    )
    assert initial_breach_pct <= cap < reprobe_breach_pct

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=initial_reference_price)
    harness.provider.fetch_last_price = AsyncMock(
        side_effect=[initial_reference_price, reprobe_reference_price]
    )
    counter = qb_live_conditional_guard_total.labels(outcome="breach_capped")
    before = counter._value.get()

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=float(cap),
    )

    assert harness.provider.fetch_last_price.await_count == 2
    harness.order_service.execute.assert_not_awaited()
    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_reprobe_within_cap_still_converts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = Decimal("1")
    initial_reference_price = Decimal("100.5")
    reprobe_reference_price = Decimal("100.75")
    initial_breach_pct = (
        abs(initial_reference_price - Decimal("100")) / initial_reference_price * Decimal("100")
    )
    reprobe_breach_pct = (
        abs(reprobe_reference_price - Decimal("100")) / reprobe_reference_price * Decimal("100")
    )
    assert initial_breach_pct <= cap
    assert reprobe_breach_pct <= cap

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=initial_reference_price)
    harness.provider.fetch_last_price = AsyncMock(
        side_effect=[initial_reference_price, reprobe_reference_price]
    )

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=float(cap),
    )

    assert harness.provider.fetch_last_price.await_count == 2
    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_interval_skips_conversion(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.common.metrics import qb_live_conditional_guard_total

    session = _session()
    session.interval = "2h"
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    counter = qb_live_conditional_guard_total.labels(outcome="convert_suppressed")
    before = counter._value.get()

    with caplog.at_level(logging.WARNING):
        await _reconcile(session, _result([_pending()]), harness)

    harness.provider.fetch_last_price.assert_awaited_once_with(ANY, session.symbol)
    harness.order_repo.has_recent_market_converted_entry.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()
    assert counter._value.get() == before + 1
    assert any(
        record.message == "live_conditional_reconcile_market_convert_suppressed"
        and getattr(record, "reason", None) == "unknown_interval"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_deferred_legs_after_conversion_are_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.common.metrics import qb_live_conditional_reconcile_errors_total

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    counter = qb_live_conditional_reconcile_errors_total.labels(
        stage="deferred_after_market_convert"
    )
    before = counter._value.get()

    await _reconcile(session, _result([_pending("a"), _pending("b")]), harness)

    assert harness.order_service.execute.await_count == 1
    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_market_conversion_stops_further_placements_in_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending("a"), _pending("b")]), harness)

    assert harness.order_service.execute.await_count == 1
    assert harness.order_service.execute.await_args.args[0].trigger_price is None


@pytest.mark.asyncio
async def test_converted_order_has_no_trigger_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price is None
    assert request.trigger_direction is None
    assert request.trigger_by is None


@pytest.mark.asyncio
async def test_converted_order_uses_distinct_idempotency_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    key = harness.order_service.execute.await_args.kwargs["idempotency_key"]
    assert key is not None
    assert ":condmkt:" in key
    assert key != build_conditional_entry_key(
        session.id, "entry", _BAR_TIME, Decimal("100"), Decimal("1")
    )


@pytest.mark.asyncio
async def test_converted_key_is_not_parsed_as_resting_conditional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    key = harness.order_service.execute.await_args.kwargs["idempotency_key"]
    assert key == build_market_converted_entry_key(
        session.id, "entry", _BAR_TIME, Decimal("100"), Decimal("1")
    )
    assert parse_conditional_entry_key(key) is None


@pytest.mark.asyncio
async def test_missing_actual_places_conditional_market_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price == Decimal("100")
    assert request.trigger_direction == 1
    assert request.type.value == "market"
    assert request.price is None


@pytest.mark.asyncio
async def test_matching_exchange_actual_is_not_replaced(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    order = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(
        monkeypatch,
        exchange_orders=[_exchange_order(order)],
        database_orders=[order],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()
    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_disappeared_desired_cancels_resting_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    order = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(monkeypatch, local_orders=[order])

    await _reconcile(session, _result([]), harness)

    harness.provider.cancel_order.assert_awaited_once_with(ANY, "exchange-entry", "BTC/USDT")
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_exchange_order_is_never_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    foreign_order = _order(
        session, trade_id="otherleg", strategy_id=uuid4(), exchange_order_id="foreign-entry"
    )
    unlinked_order = ConditionalOrderSnapshot(
        order_id="unlinked-entry",
        side="buy",
        kind="other",
        price=None,
        trigger_price=Decimal("100"),
        qty=Decimal("1"),
        reduce_only=False,
        position_idx=0,
        order_link_id="not-a-uuid",
    )
    harness = _patch_reconcile(
        monkeypatch,
        exchange_orders=[unlinked_order, _exchange_order(foreign_order)],
        database_orders=[foreign_order],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_local_in_flight_order_prevents_duplicate_placement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    local_order = _order(session)
    harness = _patch_reconcile(monkeypatch, local_orders=[local_order])

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_service_error_does_not_escape_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, execute_error=RuntimeError("gate failed"))

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_precision_failure_skips_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, precision_error=RuntimeError("markets unavailable"))

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_hedge_positions_abort_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        positions=[
            PositionSnapshot(
                side="long",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=1,
            ),
            PositionSnapshot(
                side="short",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=2,
            ),
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_hedge_positions_also_cancel_our_resting_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hedge mode 는 발주만 멈추는 게 아니라 이미 올려둔 우리 주문도 걷는다.

    포지션 산술을 더 이상 신뢰할 수 없는 상태인데 기존 조건부 진입을 남겨두면 그게
    잘못된 전제 위에서 체결된다. 취소는 포지션을 늘리지 않으므로 어느 경우에도 안전하다.
    """
    session = _session()
    resting = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[resting],
        exchange_orders=[_exchange_order(resting)],
        positions=[
            PositionSnapshot(
                side="long",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=1,
            ),
            PositionSnapshot(
                side="short",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=2,
            ),
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()
    harness.provider.cancel_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_strategy_session_on_same_account_symbol_stands_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 계정·심볼에 다른 전략 세션이 살아 있으면 사이징 전제가 깨진다.

    활성 세션 unique 키가 `strategy_id` 를 포함하므로 구조적으로 허용되는 배치다.
    reconciler 는 **계정 전체** 순포지션을 세션별 target 에서 빼므로, 전략 A 가 +1 을
    보유한 상태에서 전략 B 가 -1 을 목표하면 B 는 수량 2 를 내 A 의 포지션까지 닫고
    반전시킨다. 그래서 stand-down 하고 우리 주문을 걷는다.
    """
    session = _session()
    resting = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[resting],
        exchange_orders=[_exchange_order(resting)],
        active_sessions=[
            SimpleNamespace(
                id=uuid4(),  # 다른 세션
                strategy_id=uuid4(),  # 다른 전략
                exchange_account_id=session.exchange_account_id,
                symbol=session.symbol,  # 같은 심볼
            )
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()
    harness.provider.cancel_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_session_on_different_symbol_does_not_stand_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 같은 계정이라도 심볼이 다르면 포지션이 섞이지 않는다.

    이게 GREEN 을 유지해야 위 가드가 과잉차단이 아님이 증명된다.
    """
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        active_sessions=[
            SimpleNamespace(
                id=uuid4(),
                strategy_id=uuid4(),
                exchange_account_id=session.exchange_account_id,
                symbol="ETH/USDT",  # 다른 심볼
            )
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_same_session_in_active_list_does_not_stand_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 자기 자신은 계정 활성 목록에 당연히 들어 있다.

    `other.id != sess.id` 를 빠뜨리면 모든 세션이 영원히 stand-down 한다(기능 전면 정지).
    """
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        active_sessions=[
            SimpleNamespace(
                id=session.id,
                strategy_id=session.strategy_id,
                exchange_account_id=session.exchange_account_id,
                symbol=session.symbol,
            )
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_local_order_from_another_session_is_never_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★로컬 경로의 세션 검사. 같은 전략·계정에 세션이 2개면 이게 유일한 방벽이다.

    `list_resting_conditional_entries` 는 strategy_id + account_id 만 좁히므로,
    key 의 session_id 검사를 빼면 다른 세션의 진입 주문을 취소하게 된다.
    """
    session = _session()
    other_session = _session()
    stale = _order(other_session, trade_id="otherleg", exchange_order_id="other-session-entry")
    harness = _patch_reconcile(monkeypatch, local_orders=[stale])

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_exchange_order_from_another_account_is_never_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """거래소 경로의 exchange_account_id 검사."""
    session = _session()
    foreign = _order(session, trade_id="otherleg", exchange_order_id="foreign-account-entry")
    foreign.exchange_account_id = uuid4()
    harness = _patch_reconcile(
        monkeypatch, exchange_orders=[_exchange_order(foreign)], database_orders=[foreign]
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_reduce_only_order_is_never_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """★사용자의 손절을 지우는 것이 이 스프린트가 낼 수 있는 최악의 결함이다."""
    session = _session()
    stop_loss = _order(session, trade_id="otherleg", exchange_order_id="stop-loss-leg")
    stop_loss.reduce_only = True
    harness = _patch_reconcile(
        monkeypatch, exchange_orders=[_exchange_order(stop_loss)], database_orders=[stop_loss]
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_placed_order_carries_parseable_conditional_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★발주에 실린 key 를 검사한다. 마이그레이션-0 기전 전체가 여기 달려 있다."""
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness)

    key = harness.order_service.execute.await_args.kwargs["idempotency_key"]
    assert parse_conditional_entry_key(key) == (session.id, "entry")


@pytest.mark.asyncio
async def test_reconcile_defers_while_market_orders_are_in_flight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★같은 tick 의 시장가 dispatch 가 아직 거래소에 반영되기 전이면 미룬다.

    그 포지션으로 사이징하면 초과 수량 주문이 나간다(실측 예: 의도의 3배).
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness, market_orders_in_flight=True)

    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


# ── BL-499 취소↔dispatch 경합의 패자 경로 ─────────────────────────────────


def _capture_error_stages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`qb_live_conditional_reconcile_errors_total` 의 stage 라벨을 수집한다."""
    stages: list[str] = []
    metric = MagicMock()
    metric.labels = MagicMock(side_effect=lambda stage: (stages.append(stage), MagicMock())[1])
    monkeypatch.setattr(live_signal_module, "qb_live_conditional_reconcile_errors_total", metric)
    return stages


@pytest.mark.asyncio
async def test_cancel_race_is_classified_and_skips_placement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★경합 패배는 진짜 실패와 구분되고, 그 tick 의 등재는 하지 않는다.

    실행 워커가 `pending → submitted` 를 먼저 커밋하면 DB-only 취소는 rowcount 0 이다.
    이것은 실패가 아니라 패배이므로 `cancel_raced` 로 분류한다. 그래도 `to_place` 는
    건너뛴다 — `current_position` 은 취소 루프보다 먼저 찍은 스냅샷이라, 패배한 주문이
    그 사이 체결되면 낡은 포지션 위에서 사이징한 주문이 나간다.
    """
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=OrderState.submitted,
    )
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    assert stages == ["cancel_raced"]
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_race_does_not_touch_active_orders_gauge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★패배는 terminal 전이가 아니다. dec 하면 게이지가 음수로 표류한다."""
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=OrderState.filled,
    )
    _capture_error_stages(monkeypatch)
    gauge = MagicMock()
    monkeypatch.setattr(live_signal_module, "qb_active_orders", gauge)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    gauge.dec.assert_not_called()
    harness.order_repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_row_is_still_a_genuine_cancel_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — 행 자체가 없으면 여전히 실패다. 완화가 진짜 실패를 삼키면 안 된다."""
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=None,
    )
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    assert stages == ["cancel"]
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_next_tick_cancels_the_raced_order_on_the_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★자가 치유 — 패배한 주문은 다음 tick 에 `exchange_order_id` 로 정상 취소된다."""
    session = _session()
    raced = _order(session, trade_id="old", exchange_order_id="exchange-old")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[raced],
        exchange_orders=[_exchange_order(raced)],
        database_orders=[raced],
    )

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    harness.provider.cancel_order.assert_awaited_once_with(ANY, "exchange-old", session.symbol)


# ── BL-500 거래소 부재가 로컬 행을 이긴다 ─────────────────────────────────


@pytest.mark.asyncio
async def test_missing_order_confirmed_cancelled_is_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★거래소가 "취소됨" 이라고 확인해 주면 `actual` 에서 빠지고 재등재된다.

    이걸 안 하면 그 trade_id 는 영구 no-op 이다 — 계획기가 로컬 행만 보고
    "이미 등재됨" 으로 판정하기 때문이다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="cancelled"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.fetch_order.assert_awaited_once()
    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_order_still_open_on_exchange_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★목록에 없다고 사라진 것이 아니다.

    주문 조회 응답이 열화(레이트리밋·부분 응답)됐거나 방금 트리거돼 목록에서만
    먼저 빠졌을 수 있다. 거래소가 아직 살아 있다고 말하면 그대로 둔다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="submitted"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_probe_failure_removes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """★확인하지 못하면 그대로 둔다.

    이 함수의 다른 모든 열화 입력은 fail-closed 다. 여기만 "주문을 더 낸다" 방향으로
    fail-open 하면 REST 한 번의 열화가 중복 등재로 번역된다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[ghost],
        exchange_orders=[],
        probe_error=RuntimeError("rate limited"),
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_fill_stands_down_this_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★체결이 확인되면 이번 tick 은 등재하지 않는다.

    포지션 스냅샷은 이 확인보다 앞서 찍혔을 수 있다. 낡은 포지션으로 사이징하면
    이중 포지션이 된다 — 다음 tick 이 새 포지션으로 다시 계획한다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="filled"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_fill_does_not_increment_exchange_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """체결 확인은 거래소 부재 오류가 아니므로 error metric을 올리지 않는다."""
    from src.common.metrics import qb_live_conditional_reconcile_errors_total

    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="filled"
    )
    counter = qb_live_conditional_reconcile_errors_total.labels(stage="exchange_missing")
    before = counter._value.get()

    await _reconcile(session, _result([_pending()]), harness)

    assert counter._value.get() == before


@pytest.mark.asyncio
async def test_cancelled_probe_still_increments_exchange_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조: 취소 확인은 기존처럼 거래소 부재 오류로 계측한다."""
    from src.common.metrics import qb_live_conditional_reconcile_errors_total

    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="cancelled"
    )
    counter = qb_live_conditional_reconcile_errors_total.labels(stage="exchange_missing")
    before = counter._value.get()

    await _reconcile(session, _result([_pending()]), harness)

    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_in_flight_order_without_exchange_id_is_never_probed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — `exchange_order_id` 가 없는 행은 물어볼 대상 자체가 없다.

    그건 아직 dispatch 가 거래소 id 를 붙이지 못한 in-flight 행이고, 지우면 진짜
    이중 등재 방어가 무너진다.
    """
    session = _session()
    in_flight = _order(session, exchange_order_id=None)
    harness = _patch_reconcile(monkeypatch, local_orders=[in_flight], exchange_orders=[])

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.fetch_order.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_exchange_lookup_failure_removes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★조회 실패 tick 에는 현상 유지다. 실패를 "거래소에 없다" 로 읽으면 안 된다."""
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[ghost],
        exchange_orders_error=RuntimeError("exchange unavailable"),
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_submitted_without_exchange_id_is_deferred_to_janitor(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """★`submitted` 인데 거래소 id 가 없으면 경합이 아니라 제출 중단이다.

    dispatch 가 상태만 커밋하고 거래소 왕복에서 죽으면 그 행은 영구 고착하는데
    `orphan_scanner` 는 조건부 진입을 면제한다. 경합 카운터로 강등하면 영구 장애가
    1회성 경합에 섞여 사라진다.
    """
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=OrderState.submitted,
        fresh_exchange_order_id=None,
    )
    stages = _capture_error_stages(monkeypatch)
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    assert stages == ["cancel_deferred"]
    assert "live_conditional_reconcile_cancel_deferred_to_janitor" in caplog.messages

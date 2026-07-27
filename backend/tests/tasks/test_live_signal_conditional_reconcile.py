# 조건부 진입 reconcile의 거래소 배선과 귀속 불변식을 검증한다.
from __future__ import annotations

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
) -> SimpleNamespace:
    session = AsyncMock()
    order_repo = AsyncMock()
    order_repo.list_resting_conditional_entries = AsyncMock(return_value=local_orders or [])
    orders_by_id = {order.id: order for order in database_orders or local_orders or []}

    async def get_by_id(order_id: UUID) -> SimpleNamespace | None:
        return orders_by_id.get(order_id)

    order_repo.get_by_id = AsyncMock(side_effect=get_by_id)
    order_repo.transition_to_cancelled = AsyncMock(return_value=1)
    order_repo.transition_pending_to_cancelled = AsyncMock(return_value=1)
    order_repo.commit = AsyncMock()

    account_repo = AsyncMock()
    kill_switch_repo = AsyncMock()
    kill_switch_repo.get_active = AsyncMock(return_value=None)

    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.kill_switch_event_repository as kill_switch_repo_module
    import src.trading.repositories.order_repository as order_repo_module

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
    provider.fetch_open_conditional_orders = AsyncMock(return_value=exchange_orders or [])
    provider.fetch_open_positions = AsyncMock(return_value=positions or [])
    provider.cancel_order = AsyncMock()

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
) -> None:
    await live_signal_module._reconcile_conditional_entries(
        session,
        result,
        StrategySettings(leverage=2, margin_mode="cross", position_size_pct=10),
        harness.sm,
        bar_time=_BAR_TIME,
        market_orders_in_flight=market_orders_in_flight,
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
    first = build_conditional_entry_key(session_id, args[0], datetime(2026, 5, 1, 12, 0, tzinfo=UTC), *args[1:])
    second = build_conditional_entry_key(session_id, args[0], datetime(2026, 5, 1, 13, 0, tzinfo=UTC), *args[1:])

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

    assert build_conditional_entry_key(session_id, "  ", bar_time, Decimal("1"), Decimal("1")) is None
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

    harness.provider.cancel_order.assert_awaited_once_with(
        ANY, "exchange-entry", "BTC/USDT"
    )
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_exchange_order_is_never_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    foreign_order = _order(session, trade_id="otherleg", strategy_id=uuid4(), exchange_order_id="foreign-entry")
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

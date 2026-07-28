"""라이브 청산 parity 입력을 읽기 전용으로 조합한다."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.market_data.constants import to_bybit_raw_symbol
from src.trading.models import ExchangeExit, LiveSignalEvent, LiveSignalEventStatus, Order
from src.trading.outcome_parity import ParityBuckets, ParityObservation
from src.trading.repositories.order_repository import SessionScope, _session_scope_where


def _sum_decimals(values: Iterable[Decimal]) -> Decimal:
    """금융 합산을 Decimal 영역에서만 수행한다."""
    total = Decimal("0")
    for value in values:
        total = Decimal(str(total)) + Decimal(str(value))
    return total


def _required_decimal(value: Decimal | None, *, source: str) -> Decimal:
    """이 출력 계약에서 결측을 표현할 수 없는 확정 손익을 확인한다."""
    if value is None:
        raise ValueError(f"{source} requires realized_pnl")
    return Decimal(str(value))


def _derive_ledger_values(
    exchange_exits: Sequence[ExchangeExit],
    filled_quantity: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """한 주문의 원장 행이 단 하나일 때만 gross 와 notional 을 분해한다."""
    if len(exchange_exits) != 1 or filled_quantity is None:
        return None, None

    exchange_exit = exchange_exits[0]
    if (
        exchange_exit.closed_size is None
        or exchange_exit.avg_entry_price is None
        or exchange_exit.avg_exit_price is None
    ):
        return None, None

    closed_size = Decimal(str(exchange_exit.closed_size))
    # 원장이 이 주문의 청산 전부를 담고 있는지 확인하는 유일한 방법이 수량 대조다.
    ledger_closed_size = _sum_decimals(
        Decimal(str(exchange_exit.closed_size)) for exchange_exit in exchange_exits
    )
    if ledger_closed_size != Decimal(str(filled_quantity)):
        return None, None

    avg_entry_price = Decimal(str(exchange_exit.avg_entry_price))
    avg_exit_price = Decimal(str(exchange_exit.avg_exit_price))
    if exchange_exit.side == "Buy":
        actual_gross = (avg_entry_price - avg_exit_price) * closed_size
    elif exchange_exit.side == "Sell":
        actual_gross = (avg_exit_price - avg_entry_price) * closed_size
    else:
        return None, None
    round_trip_notional = (avg_entry_price + avg_exit_price) * closed_size
    return actual_gross, round_trip_notional


class ParityRepository:
    """세션 이벤트, 확정 주문, 거래소 청산 원장을 parity 입력으로 읽는다."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_parity_inputs(
        self,
        *,
        session_ids: Sequence[UUID],
        scopes: Sequence[SessionScope],
    ) -> tuple[list[ParityObservation], ParityBuckets]:
        """세션들의 기대 이벤트와 확정 주문을 분리해 parity 입력을 만든다."""
        if not session_ids and not scopes:
            return [], _empty_buckets()

        events = await self._load_close_events(session_ids)
        actual_orders = await self._load_confirmed_orders(scopes)
        actual_orders_by_id = {order.id: order for order in actual_orders}

        expected_by_order: dict[UUID, list[Decimal]] = defaultdict(list)
        expected_only_values: list[Decimal] = []
        expected_only_counts = {
            LiveSignalEventStatus.pending: 0,
            LiveSignalEventStatus.failed: 0,
            LiveSignalEventStatus.dispatched: 0,
        }
        for event in events:
            if event.order_id in actual_orders_by_id:
                expected_by_order[event.order_id].append(
                    _required_decimal(event.realized_pnl, source="close event")
                )
                continue

            expected_only_counts[event.status] += 1
            if event.realized_pnl is not None:
                expected_only_values.append(Decimal(str(event.realized_pnl)))

        matched_orders = [order for order in actual_orders if order.id in expected_by_order]
        exchange_exits_by_order = await self._load_exchange_exits_for_orders(matched_orders)

        observations: list[ParityObservation] = []
        for order in matched_orders:
            actual_gross, round_trip_notional = _derive_ledger_values(
                exchange_exits_by_order.get(order.id, []), order.filled_quantity
            )
            observations.append(
                ParityObservation(
                    expected_gross=_sum_decimals(expected_by_order[order.id]),
                    actual_net=_required_decimal(order.realized_pnl, source="confirmed order"),
                    actual_gross=actual_gross,
                    round_trip_notional=round_trip_notional,
                )
            )

        actual_only_orders = [order for order in actual_orders if order.id not in expected_by_order]
        buckets = ParityBuckets(
            expected_only_count=sum(expected_only_counts.values()),
            expected_only_gross=_sum_decimals(expected_only_values),
            expected_only_pending_count=expected_only_counts[LiveSignalEventStatus.pending],
            expected_only_failed_count=expected_only_counts[LiveSignalEventStatus.failed],
            expected_only_dispatched_count=expected_only_counts[LiveSignalEventStatus.dispatched],
            actual_only_count=len(actual_only_orders),
            actual_only_net=_sum_decimals(
                _required_decimal(order.realized_pnl, source="confirmed order")
                for order in actual_only_orders
            ),
            unattributed_count=await self._count_unattributed_exchange_exits(scopes),
        )
        return observations, buckets

    async def _load_close_events(self, session_ids: Sequence[UUID]) -> list[LiveSignalEvent]:
        if not session_ids:
            return []

        # 이벤트에는 전략, 계정, 심볼 열이 없다. 이 축의 스코프는 session_id FK 뿐이다.
        result = await self.session.execute(
            select(LiveSignalEvent)
            .where(LiveSignalEvent.session_id.in_(session_ids))  # type: ignore[attr-defined]
            .where(cast(Any, LiveSignalEvent.action) == "close")
        )
        return list(result.scalars().all())

    async def _load_confirmed_orders(self, scopes: Sequence[SessionScope]) -> list[Order]:
        if not scopes:
            return []

        # 주문 축은 SessionScope 의 유일한 SQL 번역을 그대로 재사용한다.
        scope_predicates = [and_(*_session_scope_where(scope)) for scope in scopes]
        result = await self.session.execute(
            select(Order)
            .where(or_(*scope_predicates))
            .where(Order.realized_pnl_synced_at.is_not(None))  # type: ignore[union-attr]
            .order_by(
                Order.filled_at.asc(),  # type: ignore[union-attr]
                cast(Any, Order.id).asc(),
            )
        )
        return list(result.scalars().all())

    async def _load_exchange_exits_for_orders(
        self,
        orders: Sequence[Order],
    ) -> dict[UUID, list[ExchangeExit]]:
        if not orders:
            return {}

        match_predicates = [
            and_(
                cast(Any, ExchangeExit.exchange_account_id) == order.exchange_account_id,
                or_(
                    cast(Any, ExchangeExit.matched_order_id) == order.id,
                    cast(Any, ExchangeExit.order_link_id) == str(order.id),
                ),
            )
            for order in orders
        ]
        result = await self.session.execute(select(ExchangeExit).where(or_(*match_predicates)))

        order_ids_by_match = {(order.exchange_account_id, order.id): order.id for order in orders}
        order_ids_by_link = {
            (order.exchange_account_id, str(order.id)): order.id for order in orders
        }
        exchange_exits_by_order: dict[UUID, list[ExchangeExit]] = defaultdict(list)
        for exchange_exit in result.scalars().all():
            order_id: UUID | None = None
            if exchange_exit.matched_order_id is not None:
                order_id = order_ids_by_match.get(
                    (exchange_exit.exchange_account_id, exchange_exit.matched_order_id)
                )
            if order_id is None and exchange_exit.order_link_id is not None:
                order_id = order_ids_by_link.get(
                    (exchange_exit.exchange_account_id, exchange_exit.order_link_id)
                )
            if order_id is not None:
                exchange_exits_by_order[order_id].append(exchange_exit)
        return dict(exchange_exits_by_order)

    async def _count_unattributed_exchange_exits(self, scopes: Sequence[SessionScope]) -> int:
        if not scopes:
            return 0

        ledger_scope_predicates = [
            and_(
                cast(Any, ExchangeExit.exchange_account_id) == scope.exchange_account_id,
                cast(Any, ExchangeExit.symbol) == to_bybit_raw_symbol(scope.symbol),
            )
            for scope in scopes
        ]
        exchange_exits_result = await self.session.execute(
            select(ExchangeExit).where(or_(*ledger_scope_predicates))
        )
        account_ids = {scope.exchange_account_id for scope in scopes}
        known_orders_result = await self.session.execute(
            select(cast(Any, Order.exchange_account_id), cast(Any, Order.id)).where(
                cast(Any, Order.exchange_account_id).in_(account_ids)
            )
        )
        known_order_ids: dict[UUID, set[str]] = defaultdict(set)
        for exchange_account_id, order_id in known_orders_result.all():
            known_order_ids[exchange_account_id].add(str(order_id))

        return sum(
            1
            for exchange_exit in exchange_exits_result.scalars().all()
            if exchange_exit.matched_order_id is None
            and exchange_exit.order_link_id
            not in known_order_ids[exchange_exit.exchange_account_id]
        )


def _empty_buckets() -> ParityBuckets:
    return ParityBuckets(
        expected_only_count=0,
        expected_only_gross=Decimal("0"),
        expected_only_pending_count=0,
        expected_only_failed_count=0,
        expected_only_dispatched_count=0,
        actual_only_count=0,
        actual_only_net=Decimal("0"),
        unattributed_count=0,
    )

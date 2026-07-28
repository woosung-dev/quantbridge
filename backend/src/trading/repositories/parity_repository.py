"""라이브 청산 parity 입력을 읽기 전용으로 조합한다."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, cast
from uuid import UUID

from sqlalchemy import String, and_, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from src.market_data.constants import to_bybit_raw_symbol
from src.trading.models import (
    ExchangeExit,
    ExitClassification,
    LiveSignalEvent,
    LiveSignalEventStatus,
    Order,
    OrderState,
)
from src.trading.outcome_parity import (
    PARITY_DECIMAL_CONTEXT,
    ParityBuckets,
    ParityObservation,
)
from src.trading.repositories.order_repository import SessionScope, _session_scope_where

_LEDGER_ONLY_CLASSIFICATIONS = (
    ExitClassification.ours,
    ExitClassification.bracket_tp,
    ExitClassification.bracket_sl,
    ExitClassification.trailing,
    ExitClassification.liquidation,
)


@dataclass(frozen=True, slots=True)
class AccountLedgerDiagnostics:
    """계정 전체, 기간 무관 미귀속 원장 진단이다."""

    unattributed_count: int


@dataclass(frozen=True, slots=True)
class LedgerOnlyDiagnostics:
    """한 세션 또는 전략 누적 스코프에 속한 원장 전용 청산이다."""

    ledger_only_count: int
    ledger_only_net: Decimal


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
    with localcontext(PARITY_DECIMAL_CONTEXT):
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
            ledger_only_count=0,
            ledger_only_net=Decimal("0"),
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

    async def load_account_ledger_diagnostics(
        self,
        scopes: Sequence[SessionScope],
    ) -> AccountLedgerDiagnostics:
        """계정 전체, 기간 무관 미귀속 원장 행을 SQL 집계로 읽는다."""
        if not scopes:
            return AccountLedgerDiagnostics(unattributed_count=0)

        ledger_scope_predicates = [
            and_(
                cast(Any, ExchangeExit.exchange_account_id) == scope.exchange_account_id,
                cast(Any, ExchangeExit.symbol) == to_bybit_raw_symbol(scope.symbol),
            )
            for scope in scopes
        ]
        has_local_order = (
            select(cast(Any, Order.id))
            .where(cast(Any, Order.exchange_account_id) == ExchangeExit.exchange_account_id)
            .where(sa_cast(cast(Any, Order.id), String) == ExchangeExit.order_link_id)
            .exists()
        )
        scoped_exits = (
            select(
                cast(Any, ExchangeExit.exchange_order_id),
                cast(Any, ExchangeExit.exchange_created_at),
                cast(Any, ExchangeExit.closed_pnl),
                cast(Any, ExchangeExit.classification),
                cast(Any, ExchangeExit.matched_order_id),
                cast(Any, ExchangeExit.order_link_id),
                has_local_order.label("has_local_order"),
            )
            .where(or_(*ledger_scope_predicates))
            .cte("scoped_exchange_exits")
        )
        unlinked_exit = and_(
            scoped_exits.c.matched_order_id.is_(None),
            or_(
                scoped_exits.c.order_link_id.is_(None),
                scoped_exits.c.has_local_order.is_(False),
            ),
        )
        unattributed_count = (
            select(func.count())
            .select_from(scoped_exits)
            .where(unlinked_exit)
            .where(~scoped_exits.c.classification.in_(_LEDGER_ONLY_CLASSIFICATIONS))
            .scalar_subquery()
        )
        result = await self.session.execute(select(unattributed_count))
        return AccountLedgerDiagnostics(unattributed_count=int(result.scalar_one()))

    async def load_scoped_ledger_only_diagnostics(
        self,
        scopes: Sequence[SessionScope],
    ) -> LedgerOnlyDiagnostics:
        """원장 전용 청산을 세션 또는 전략 누적 범위에서 주문 단위로 집계한다."""
        if not scopes:
            return LedgerOnlyDiagnostics(ledger_only_count=0, ledger_only_net=Decimal("0"))

        ledger_scope_predicates: list[Any] = []
        confirmed_close_scope_predicates: list[Any] = []
        for scope in scopes:
            linked_order_scope = [
                cast(Any, Order.strategy_id) == scope.strategy_id,
                cast(Any, Order.exchange_account_id) == scope.exchange_account_id,
                cast(Any, Order.symbol) == scope.symbol,
                cast(Any, Order.state) == OrderState.filled,
                cast(Any, Order.filled_at) >= scope.started_at,
            ]
            ledger_scope = [
                cast(Any, ExchangeExit.exchange_account_id) == scope.exchange_account_id,
                cast(Any, ExchangeExit.symbol) == to_bybit_raw_symbol(scope.symbol),
                cast(Any, ExchangeExit.exchange_created_at) >= scope.started_at,
            ]
            confirmed_close_scope = [
                cast(Any, Order.strategy_id) == scope.strategy_id,
                cast(Any, Order.exchange_account_id) == scope.exchange_account_id,
                cast(Any, Order.symbol) == scope.symbol,
                cast(Any, Order.state) == OrderState.filled,
                cast(Any, Order.filled_at) >= scope.started_at,
            ]
            if scope.ended_at is not None:
                # 거래소 청산 시계와 우리 주문의 filled_at 시계는 다르므로 이 경계는 근사다.
                ledger_scope.append(cast(Any, ExchangeExit.exchange_created_at) < scope.ended_at)
                linked_order_scope.append(cast(Any, Order.filled_at) < scope.ended_at)
                confirmed_close_scope.append(cast(Any, Order.filled_at) < scope.ended_at)
            confirmed_close_scope_predicates.append(and_(*confirmed_close_scope))

            has_scoped_linked_order = (
                select(cast(Any, Order.id))
                .where(cast(Any, Order.exchange_account_id) == ExchangeExit.exchange_account_id)
                .where(sa_cast(cast(Any, Order.id), String) == ExchangeExit.order_link_id)
                .where(and_(*linked_order_scope))
                .exists()
            )
            ledger_scope.append(
                or_(
                    cast(Any, ExchangeExit.attributed_strategy_id) == scope.strategy_id,
                    has_scoped_linked_order,
                )
            )
            ledger_scope_predicates.append(and_(*ledger_scope))

        has_confirmed_close_order = (
            select(cast(Any, Order.id))
            .where(cast(Any, Order.exchange_account_id) == ExchangeExit.exchange_account_id)
            .where(sa_cast(cast(Any, Order.id), String) == ExchangeExit.order_link_id)
            .where(Order.realized_pnl_synced_at.is_not(None))  # type: ignore[union-attr]
            .where(cast(Any, Order.reduce_only).is_(True))
            .where(or_(*confirmed_close_scope_predicates))
            .exists()
        )
        scoped_exits = (
            select(
                cast(Any, ExchangeExit.exchange_account_id),
                cast(Any, ExchangeExit.exchange_order_id),
                cast(Any, ExchangeExit.closed_pnl),
                cast(Any, ExchangeExit.classification),
                cast(Any, ExchangeExit.matched_order_id),
                has_confirmed_close_order.label("has_confirmed_close_order"),
            )
            .where(or_(*ledger_scope_predicates))
            .cte("scoped_ledger_only_exits")
        )
        ledger_only_exits = (
            select(
                scoped_exits.c.exchange_account_id,
                scoped_exits.c.exchange_order_id,
                # 분할 행 합산 규칙은 aggregate_closed_pnl_by_order 와 같아야 한다.
                func.sum(scoped_exits.c.closed_pnl).label("closed_pnl"),
            )
            .where(scoped_exits.c.matched_order_id.is_(None))
            .where(scoped_exits.c.has_confirmed_close_order.is_(False))
            .where(scoped_exits.c.classification.in_(_LEDGER_ONLY_CLASSIFICATIONS))
            .group_by(scoped_exits.c.exchange_account_id, scoped_exits.c.exchange_order_id)
            .cte("ledger_only_exchange_exits")
        )
        ledger_only_count = select(func.count()).select_from(ledger_only_exits).scalar_subquery()
        ledger_only_net = (
            select(func.coalesce(func.sum(ledger_only_exits.c.closed_pnl), Decimal("0")))
            .select_from(ledger_only_exits)
            .scalar_subquery()
        )
        result = await self.session.execute(select(ledger_only_count, ledger_only_net))
        count, net = result.one()
        return LedgerOnlyDiagnostics(
            ledger_only_count=int(count),
            ledger_only_net=Decimal(str(net)),
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
        ledger_only_count=0,
        ledger_only_net=Decimal("0"),
    )

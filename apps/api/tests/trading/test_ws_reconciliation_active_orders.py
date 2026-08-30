"""Sprint 16 BL-027 — reconciliation winner-only commit-then-dec (codex G.0 P1 #1).

핵심:
- `_apply_transition` 은 rowcount: int return + dec 호출 X (caller responsibility)
- `run()` 는 loop 안 transition 의 winner 누적 → session.commit() 성공 후 dec 발화
- 이전: dec() 자체가 누락 → reconcile transition 시 gauge 감소 안 됨 (drift)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.common.metrics import qb_active_orders, qb_partial_fill_total
from src.trading.models import (
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.services.websocket_reconciliation_service import WebSocketReconciliationService


def _build_order(state: OrderState = OrderState.submitted) -> Order:
    return Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=state,
        idempotency_key=None,
        idempotency_payload_hash=None,
        leverage=None,
        margin_mode=None,
        created_at=datetime.now(UTC),
    )


# =============================================================================
# _apply_transition: rowcount return + dec 호출 X
# =============================================================================


@pytest.mark.asyncio
async def test_apply_transition_filled_returns_rowcount_no_dec() -> None:
    """BL-027: _apply_transition 가 rowcount return + dec 호출 X (caller responsibility)."""
    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=1)

    settings = MagicMock()
    fetcher = AsyncMock()
    reconciler = WebSocketReconciliationService(
        repo=repo,
        fetcher=fetcher,
        settings=settings,
    )

    qb_active_orders.set(1.0)
    local = _build_order()

    rc = await reconciler._apply_transition(
        local,
        OrderState.filled,
        {"average": "100.0", "filled": "0.0005", "id": "exchange-abc"},
    )

    assert rc == 1
    assert repo.transition_to_filled.await_args.kwargs["filled_quantity"] == Decimal("0.0005")
    # caller responsibility — _apply_transition 자체는 dec 안 함
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_apply_transition_loser_returns_zero() -> None:
    repo = AsyncMock()
    repo.transition_to_cancelled = AsyncMock(return_value=0)
    settings = MagicMock()
    fetcher = AsyncMock()
    reconciler = WebSocketReconciliationService(
        repo=repo,
        fetcher=fetcher,
        settings=settings,
    )

    qb_active_orders.set(1.0)
    local = _build_order()

    rc = await reconciler._apply_transition(local, OrderState.cancelled, {})

    assert rc == 0
    assert qb_active_orders._value.get() == 1.0


# =============================================================================
# run(): commit-then-dec winner-only (loop 안 multiple transitions 누적 → 일괄 dec)
# =============================================================================


class _FakeFetcher:
    """Reconciler.fetcher Protocol 호환 — 회귀 테스트용."""

    def __init__(self, exch_orders: list[dict[str, Any]]) -> None:
        self._open = exch_orders
        self._recent: list[dict[str, Any]] = []

    async def fetch_open_orders(self, account_id: UUID) -> list[dict[str, Any]]:
        _ = account_id  # protocol 매칭 — 사용 안 함
        return self._open

    async def fetch_recent_orders(
        self, account_id: UUID, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        _ = (account_id, limit)
        return self._recent


@pytest.mark.asyncio
async def test_run_filled_winner_commits_then_decs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run(): exch 가 filled status → transition_to_filled rowcount=1 → commit → dec."""
    local = _build_order()

    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=1)
    repo.list_active_by_exchange_account = AsyncMock(return_value=[local])
    repo.commit = AsyncMock()

    # _list_local_active 가 local 1건 반환하도록 monkeypatch
    settings = MagicMock()
    fetcher = _FakeFetcher(
        [
            {
                "clientOrderId": str(local.id),
                "status": "Filled",
                "average": "100.0",
                "filled": "0.0005",
                "id": "exchange-abc",
            }
        ]
    )
    reconciler = WebSocketReconciliationService(
        repo=repo,
        fetcher=fetcher,
        settings=settings,
    )

    qb_active_orders.set(1.0)
    partial_counter = qb_partial_fill_total.labels(source="reconciler", kind="entry")
    before_partial = partial_counter._value.get()

    await reconciler.run(account_id=uuid4())

    repo.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 0.0  # winner-only dec
    assert partial_counter._value.get() == before_partial + 1


@pytest.mark.asyncio
async def test_run_filled_loser_commits_no_dec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run(): rowcount=0 loser — commit OK + dec X."""
    local = _build_order()

    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=0)  # loser
    repo.list_active_by_exchange_account = AsyncMock(return_value=[local])
    repo.commit = AsyncMock()

    settings = MagicMock()
    fetcher = _FakeFetcher(
        [
            {
                "clientOrderId": str(local.id),
                "status": "Filled",
                "average": "100.0",
                "id": "exchange-abc",
            }
        ]
    )
    reconciler = WebSocketReconciliationService(
        repo=repo,
        fetcher=fetcher,
        settings=settings,
    )

    qb_active_orders.set(1.0)

    await reconciler.run(account_id=uuid4())

    repo.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 1.0  # dec X


@pytest.mark.asyncio
async def test_run_commit_failure_no_dec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex G.0 P1 #1: commit 실패 시 winner 도 dec X (silent corruption 방어)."""
    local = _build_order()

    repo = AsyncMock()
    repo.transition_to_filled = AsyncMock(return_value=1)
    repo.list_active_by_exchange_account = AsyncMock(return_value=[local])
    repo.commit = AsyncMock(side_effect=RuntimeError("commit failed"))

    settings = MagicMock()
    fetcher = _FakeFetcher(
        [
            {
                "clientOrderId": str(local.id),
                "status": "Filled",
                "average": "100.0",
                "id": "exchange-abc",
            }
        ]
    )
    reconciler = WebSocketReconciliationService(
        repo=repo,
        fetcher=fetcher,
        settings=settings,
    )

    qb_active_orders.set(1.0)

    with pytest.raises(RuntimeError):
        await reconciler.run(account_id=uuid4())

    # commit 실패 → dec 발화 X → drift 방어
    assert qb_active_orders._value.get() == 1.0


@pytest.mark.asyncio
async def test_run_multiple_transitions_winners_only_dec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run(): 2 local active. 1 winner (filled) + 1 loser (cancelled rowcount=0) → 1회 dec."""
    local_a = _build_order()
    local_b = _build_order()

    repo = AsyncMock()
    # local_a 가 winner (filled), local_b 는 loser (cancelled rowcount=0)
    repo.transition_to_filled = AsyncMock(return_value=1)
    repo.transition_to_cancelled = AsyncMock(return_value=0)
    repo.list_active_by_exchange_account = AsyncMock(return_value=[local_a, local_b])
    repo.commit = AsyncMock()

    settings = MagicMock()
    fetcher = _FakeFetcher(
        [
            {
                "clientOrderId": str(local_a.id),
                "status": "Filled",
                "average": "100.0",
                "id": "exchange-aaa",
            },
            {
                "clientOrderId": str(local_b.id),
                "status": "Cancelled",
                "id": "exchange-bbb",
            },
        ]
    )
    reconciler = WebSocketReconciliationService(
        repo=repo,
        fetcher=fetcher,
        settings=settings,
    )

    qb_active_orders.set(2.0)

    await reconciler.run(account_id=uuid4())

    repo.commit.assert_awaited_once()
    assert qb_active_orders._value.get() == 1.0  # winner 1명만 dec, 2 → 1

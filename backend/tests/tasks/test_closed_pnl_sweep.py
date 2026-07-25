# closedPnl 스윕의 그룹 조회와 고아 행 관측을 검증한다.
"""closedPnl 주기 스윕 회귀 테스트."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.models import ExchangeMode, ExchangeName
from src.trading.providers import ClosedPnlSnapshot


def _order(account_id, symbol: str, exchange_order_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        exchange_account_id=account_id,
        symbol=symbol,
        exchange_order_id=exchange_order_id,
        leverage=3,
        filled_at=datetime.now(UTC) - timedelta(minutes=1),
    )


def _account() -> SimpleNamespace:
    return SimpleNamespace(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
        passphrase_encrypted=None,
    )


def _sessionmaker(sessions: list[MagicMock]):
    @asynccontextmanager
    async def _ctx():
        yield sessions.pop(0)

    class _SM:
        def __call__(self):
            return _ctx()

    return _SM()


@pytest.mark.asyncio
async def test_sweep_groups_once_counts_orphans_and_continues_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as trading_mod

    account_a, account_b = uuid4(), uuid4()
    orders = [
        _order(account_a, "BTC/USDT", "a-1"),
        _order(account_a, "BTC/USDT", "a-2"),
        _order(account_b, "ETH/USDT", "b-1"),
    ]
    sessions = [MagicMock() for _ in range(5)]
    sessions[1].get = AsyncMock(return_value=_account())
    sessions[2].get = AsyncMock(return_value=_account())
    sessions[3].commit = AsyncMock()
    writes: list[str] = []

    class _Repo:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def list_unsynced_reduce_only_since(self, cutoff):
            return orders

        async def backfill_exchange_realized_pnl(self, order_id, **kwargs):
            writes.append(str(order_id))
            return 1

    monkeypatch.setattr(trading_mod, "OrderRepository", _Repo)
    crypto = MagicMock()
    crypto.decrypt.side_effect = ["k", "s", "k", "s"]
    monkeypatch.setattr(trading_mod, "EncryptionService", MagicMock(return_value=crypto))
    provider = MagicMock(
        fetch_closed_pnl_page=AsyncMock(
            side_effect=[
                RuntimeError("bad account"),
                [
                    ClosedPnlSnapshot("b-1", Decimal("-1"), None, None, None),
                    ClosedPnlSnapshot("exchange-native", Decimal("-2"), None, None, None),
                ],
            ]
        )
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(sessions), provider=provider, now=datetime.now(UTC)
    )

    assert provider.fetch_closed_pnl_page.await_count == 2
    assert summary == {"scanned": 3, "applied": 1, "orphan": 1, "groups": 2}
    assert writes == [str(orders[2].id)]


def test_aggregate_sums_split_closed_pnl_rows() -> None:
    """분할 closedPnl 행은 합산해야 한다 — 마지막 행만 취하면 CAS 가 부분값을 영구 고정한다.

    refresh 경로는 합산하는데 스윕만 dict 로 덮어쓰면 같은 주문이 어느 경로로 보정되느냐에
    따라 저장값이 달라진다. 두 경로 모두 aggregate_closed_pnl_by_order 를 쓰도록 고정한다.
    """
    from decimal import Decimal

    from src.trading.providers import ClosedPnlSnapshot, aggregate_closed_pnl_by_order

    rows = [
        ClosedPnlSnapshot(
            order_id="ex-1",
            closed_pnl=Decimal("-0.02"),
            closed_size=Decimal("0.0006"),
            avg_exit_price=Decimal("64000"),
            updated_at_ms=1,
        ),
        ClosedPnlSnapshot(
            order_id="ex-1",
            closed_pnl=Decimal("-0.03"),
            closed_size=Decimal("0.0004"),
            avg_exit_price=Decimal("64010"),
            updated_at_ms=2,
        ),
        ClosedPnlSnapshot(
            order_id="ex-2",
            closed_pnl=Decimal("0.5"),
            closed_size=Decimal("0.001"),
            avg_exit_price=Decimal("64020"),
            updated_at_ms=3,
        ),
    ]

    merged = aggregate_closed_pnl_by_order(rows)

    assert merged["ex-1"].closed_pnl == Decimal("-0.05000000")
    assert merged["ex-1"].closed_size == Decimal("0.0010")
    assert merged["ex-1"].updated_at_ms == 2
    assert merged["ex-2"].closed_pnl == Decimal("0.50000000")
    assert set(merged) == {"ex-1", "ex-2"}

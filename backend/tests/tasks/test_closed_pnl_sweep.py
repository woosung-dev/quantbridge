# 거래소 청산 원장 스윕의 DB 불요 회귀 계약을 검증한다.

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.trading.models import ExchangeMode, ExchangeName, ExitClassification, OrderSide
from src.trading.providers import ClosedOrderMeta, ClosedPnlSnapshot


def _account() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
        passphrase_encrypted=None,
    )


def _snapshot(
    order_id: str,
    *,
    created_at_ms: int | None,
    closed_pnl: str = "1",
    symbol: str | None = "BTC/USDT",
) -> ClosedPnlSnapshot:
    raw = {
        "orderId": order_id,
        "createdTime": str(created_at_ms) if created_at_ms is not None else None,
        "updatedTime": str(created_at_ms or 0),
        "closedSize": "1",
        "closedPnl": closed_pnl,
        "avgEntryPrice": "100",
        "avgExitPrice": "101",
        "cumExitValue": "101",
    }
    return ClosedPnlSnapshot(
        order_id=order_id,
        closed_pnl=Decimal(closed_pnl),
        closed_size=Decimal("1"),
        avg_exit_price=Decimal("101"),
        updated_at_ms=created_at_ms,
        symbol=symbol,
        side="Sell",
        avg_entry_price=Decimal("100"),
        created_at_ms=created_at_ms,
        raw=raw,
    )


def _order(account_id: UUID, exchange_order_id: str, *, synced: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=account_id,
        exchange_order_id=exchange_order_id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        reduce_only=True,
        quantity=Decimal("1"),
        filled_price=Decimal("100"),
        filled_at=datetime(2026, 7, 1, tzinfo=UTC),
        realized_pnl_synced_at=datetime(2026, 7, 1, tzinfo=UTC) if synced else None,
    )


class _State:
    def __init__(self, accounts: list[SimpleNamespace], oldest: datetime | None = None) -> None:
        self.accounts = accounts
        # 과거 스캔 경계. 원장 min 이 아니라 별도 영속 값이어야 빈 창에서 멈추지 않는다.
        self.backfilled_from = oldest
        self.rows = []
        self.row_hashes: set[str] = set()
        self.matched_orders: list[SimpleNamespace] = []
        self.attribution_orders: list[SimpleNamespace] = []
        self.unsynced_orders: list[SimpleNamespace] = []
        self.backfills: list[tuple[UUID, Decimal]] = []


def _sessionmaker():
    @asynccontextmanager
    async def context():
        session = MagicMock()
        session.commit = AsyncMock()
        yield session

    class SessionMaker:
        def __call__(self):
            return context()

    return SessionMaker()


def _install_repositories(monkeypatch: pytest.MonkeyPatch, state: _State) -> None:
    import src.tasks.trading as trading_mod

    class AccountRepository:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def list_by_exchange(self, exchange: ExchangeName):
            return state.accounts

    class ExitRepository:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def get_backfilled_from(self, account_id: UUID):
            return state.backfilled_from

        async def set_backfilled_from(self, account_id: UUID, boundary: datetime):
            # 과거로만 전진한다. 행이 0건이어도 경계는 움직여야 빈 구간에서 멈추지 않는다.
            if state.backfilled_from is None or boundary < state.backfilled_from:
                state.backfilled_from = boundary

        async def upsert_rows(self, rows):
            added = []
            for row in rows:
                if row.row_hash not in state.row_hashes:
                    state.row_hashes.add(row.row_hash)
                    state.rows.append(row)
                    added.append(row.row_hash)
            return added

        async def aggregate_closed_pnl(self, account_id: UUID, order_ids):
            sums: dict[str, Decimal] = {}
            for row in state.rows:
                if row.exchange_order_id in order_ids:
                    sums[row.exchange_order_id] = sums.get(
                        row.exchange_order_id, Decimal("0")
                    ) + row.closed_pnl
            return sums

        async def list_by_row_hashes(self, account_id: UUID, hashes):
            return [row for row in state.rows if row.row_hash in hashes]

    class OrderRepository:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def list_by_exchange_order_ids(self, account_id: UUID, order_ids):
            return [order for order in state.matched_orders if order.exchange_order_id in order_ids]

        async def list_filled_for_attribution(self, account_id: UUID):
            return state.attribution_orders

        async def list_unsynced_reduce_only(self, account_id: UUID):
            return state.unsynced_orders

        async def backfill_exchange_realized_pnl(self, order_id: UUID, *, realized_pnl, synced_at):
            state.backfills.append((order_id, realized_pnl))
            return 1

    monkeypatch.setattr(trading_mod, "ExchangeAccountRepository", AccountRepository)
    monkeypatch.setattr(trading_mod, "ExchangeExitRepository", ExitRepository)
    monkeypatch.setattr(trading_mod, "OrderRepository", OrderRepository)
    monkeypatch.setattr(
        trading_mod,
        "EncryptionService",
        MagicMock(return_value=SimpleNamespace(decrypt=lambda value: "secret")),
    )


def test_closed_pnl_windows_select_recent_and_bounded_history() -> None:
    from src.tasks.trading import _EXIT_WINDOW_MS, _closed_pnl_windows, _datetime_to_ms

    now = datetime(2026, 7, 25, tzinfo=UTC)
    now_ms = _datetime_to_ms(now)
    # 경계가 없으면 최근 창의 시작점부터 뒤로 훑기 시작한다.
    first = _closed_pnl_windows(now_ms, None)
    assert first[0] == (now_ms - _EXIT_WINDOW_MS, now_ms)
    assert first[1] == (now_ms - 2 * _EXIT_WINDOW_MS, now_ms - _EXIT_WINDOW_MS)
    historical = _closed_pnl_windows(now_ms, now - timedelta(days=30))
    assert historical[1][1] == _datetime_to_ms(now - timedelta(days=30))
    assert len(_closed_pnl_windows(now_ms, now - timedelta(days=90))) == 1


def test_closed_pnl_windows_advance_even_when_a_window_holds_no_rows() -> None:
    """빈 창에서 멈추면 그 이전 역사에 영원히 도달하지 못한다.

    실측 반증 — 원장 min(exchange_created_at) 을 진행 마커로 쓰면 07-24 행만 적재된 뒤
    07-17~07-24 빈 구간에서 정지해 07-05 행 7건(백필 대상 전량)에 도달하지 못했다.
    """
    from src.tasks.trading import _EXIT_WINDOW_MS, _closed_pnl_windows, _ms_to_datetime

    now_ms = 1_784_995_200_000  # 2026-07-25T14:00Z
    boundary = _ms_to_datetime(now_ms - _EXIT_WINDOW_MS)
    seen: list[tuple[int, int]] = []
    for _ in range(4):
        windows = _closed_pnl_windows(now_ms, boundary)
        assert len(windows) == 2, "빈 창이어도 과거 창이 계속 선택돼야 한다"
        seen.append(windows[1])
        boundary = _ms_to_datetime(windows[1][0])
    assert len(set(seen)) == 4, f"같은 창을 반복 조회하고 있다: {seen}"
    assert seen[-1][0] < seen[0][0], "경계가 과거로 전진하지 않는다"


@pytest.mark.asyncio
async def test_sweep_skips_meta_when_every_row_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    state.matched_orders = [_order(account.id, "our-close")]
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("our-close", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert provider.fetch_closed_order_meta.await_count == 0
    # 경계가 없는 계정도 최근 창 + 과거 첫 창을 함께 본다. 같은 행은 UNIQUE 로 한 번만 들어간다.
    assert summary == {"accounts": 1, "windows": 2, "inserted": 1, "backfilled": 0, "alerted": 0}
    assert state.rows[0].classification == ExitClassification.ours


@pytest.mark.asyncio
async def test_sweep_continues_when_meta_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("external", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(side_effect=RuntimeError("metadata unavailable")),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    # 창마다 미매칭 행이 있으면 창마다 한 번 보강을 시도한다.
    assert provider.fetch_closed_order_meta.await_count == 2
    assert summary["inserted"] == 1
    assert state.rows[0].classification == ExitClassification.unknown


@pytest.mark.asyncio
async def test_sweep_aggregates_ledger_rows_before_backfill(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    now = datetime(2026, 7, 25, tzinfo=UTC)
    account = _account()
    state = _State([account], oldest=now - timedelta(days=30))
    state.unsynced_orders = [_order(account.id, "split-close")]
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            side_effect=[
                [_snapshot("split-close", created_at_ms=1, closed_pnl="-0.02")],
                [_snapshot("split-close", created_at_ms=2, closed_pnl="-0.03")],
            ]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=now
    )

    assert summary["backfilled"] == 1
    assert state.backfills == [(state.unsynced_orders[0].id, Decimal("-0.05"))]


@pytest.mark.asyncio
async def test_sweep_alerts_only_new_external_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    send_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(trading_mod, "send_rule_alert", send_alert)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("external", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(return_value={"external": ClosedOrderMeta("external", "CreateByUser", None, None)}),
    )

    first = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )
    second = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert first["alerted"] == 1
    assert second["alerted"] == 0
    assert send_alert.await_count == 1


@pytest.mark.asyncio
async def test_sweep_skips_rows_without_created_or_updated_time(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[
                _snapshot("missing-time", created_at_ms=None),
                _snapshot("valid", created_at_ms=1),
            ]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert summary["inserted"] == 1
    assert [row.exchange_order_id for row in state.rows] == ["valid"]


@pytest.mark.asyncio
async def test_sweep_retries_same_historical_window_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    now = datetime(2026, 7, 25, tzinfo=UTC)
    state = _State([_account()], oldest=now - timedelta(days=30))
    _install_repositories(monkeypatch, state)
    calls: list[tuple[int, int]] = []

    async def fetch_window(creds, symbol, *, start_ms, end_ms):
        calls.append((start_ms, end_ms))
        if len(calls) % 2 == 0:
            raise RuntimeError("historical failure")
        return []

    provider = SimpleNamespace(fetch_closed_pnl_window=fetch_window, fetch_closed_order_meta=AsyncMock())

    await trading_mod._sweep_closed_pnl_with_session(_sessionmaker(), provider=provider, now=now)
    await trading_mod._sweep_closed_pnl_with_session(_sessionmaker(), provider=provider, now=now)

    assert calls[1] == calls[3]


@pytest.mark.asyncio
async def test_sweep_isolates_one_account_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account(), _account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(side_effect=[RuntimeError("first failed"), [], []]),
        fetch_closed_order_meta=AsyncMock(),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    # 첫 계정은 첫 창에서 죽고, 둘째 계정은 최근 창 + 과거 첫 창을 정상 처리한다.
    assert provider.fetch_closed_pnl_window.await_count == 3
    assert summary == {"accounts": 2, "windows": 2, "inserted": 0, "backfilled": 0, "alerted": 0}

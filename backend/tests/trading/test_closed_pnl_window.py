# Bybit closedPnl 창 조회와 원본 행 보존을 검증한다.
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.exceptions import ProviderError
from src.trading.providers import (
    _CLOSED_PNL_MAX_WINDOW_MS,
    BybitFuturesProvider,
    ClosedPnlSnapshot,
    Credentials,
    _closed_pnl_snapshot_from_position,
    aggregate_closed_pnl_by_order,
)


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(api_key="test-key", api_secret="test-secret")


def _mock_exchange(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    import ccxt.async_support as ccxt_async

    exchange = MagicMock()
    exchange.fetch_positions_history = AsyncMock(return_value=[])
    exchange.fetch_closed_orders = AsyncMock(return_value=[])
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))
    return exchange


async def test_closed_pnl_window_rejects_over_seven_days_and_accepts_exact_limit(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match=str(_CLOSED_PNL_MAX_WINDOW_MS + 1)):
        await provider.fetch_closed_pnl_window(
            credentials,
            "BTC/USDT",
            start_ms=0,
            end_ms=_CLOSED_PNL_MAX_WINDOW_MS + 1,
        )

    exchange = _mock_exchange(monkeypatch)
    assert await provider.fetch_closed_pnl_window(
        credentials,
        "BTC/USDT",
        start_ms=0,
        end_ms=_CLOSED_PNL_MAX_WINDOW_MS,
    ) == []
    exchange.fetch_positions_history.assert_awaited_once()


@pytest.mark.parametrize("start_ms,end_ms", [(1, 1), (2, 1)])
async def test_closed_pnl_window_rejects_non_positive_width(
    credentials: Credentials, start_ms: int, end_ms: int
) -> None:
    with pytest.raises(ProviderError, match=str(end_ms - start_ms)):
        await BybitFuturesProvider().fetch_closed_pnl_window(
            credentials,
            "BTC/USDT",
            start_ms=start_ms,
            end_ms=end_ms,
        )


def test_closed_pnl_snapshot_uses_raw_info_side_and_raw_decimal_strings() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "orderId": "close-1",
        "closedPnl": "-0.04524449",
        "closedSize": "0.001",
        "avgExitPrice": "64144.00000001",
        "updatedTime": "1720000000001",
        "side": "Sell",
        "avgEntryPrice": "64118.70000001",
        "qty": "0.00100001",
        "createdTime": "1720000000000",
        "execType": "Trade",
        "orderType": "Market",
        "leverage": "10",
    }
    snapshot = _closed_pnl_snapshot_from_position({"side": "long", "info": raw})

    assert snapshot is not None
    assert snapshot.side == "Sell"
    assert snapshot.avg_entry_price == Decimal("64118.70000001")
    assert snapshot.qty == Decimal("0.00100001")
    assert snapshot.created_at_ms == 1720000000000
    assert snapshot.exec_type == "Trade"
    assert snapshot.order_type == "Market"
    assert snapshot.leverage == 10
    assert snapshot.raw == raw
    assert snapshot.raw is not raw


def test_aggregate_closed_pnl_keeps_last_metadata_and_earliest_created_time() -> None:
    first = ClosedPnlSnapshot(
        "close-1",
        Decimal("-1.000000001"),
        Decimal("0.1"),
        Decimal("100"),
        200,
        symbol="FIRST",
        side="Buy",
        avg_entry_price=Decimal("90"),
        qty=Decimal("0.1"),
        created_at_ms=100,
        exec_type="First",
        order_type="Limit",
        leverage=3,
        raw={"part": "first"},
    )
    last = ClosedPnlSnapshot(
        "close-1",
        Decimal("-2.000000002"),
        Decimal("0.2"),
        Decimal("101"),
        300,
        symbol="LAST",
        side="Sell",
        avg_entry_price=Decimal("91"),
        qty=Decimal("0.2"),
        created_at_ms=150,
        exec_type="Trade",
        order_type="Market",
        leverage=10,
        raw={"part": "last"},
    )

    snapshot = aggregate_closed_pnl_by_order([first, last])["close-1"]

    assert snapshot.closed_pnl == Decimal("-3.00000000")
    assert snapshot.closed_size == Decimal("0.3")
    assert snapshot.created_at_ms == 100
    assert snapshot.symbol == "LAST"
    assert snapshot.side == "Sell"
    assert snapshot.avg_entry_price == Decimal("91")
    assert snapshot.qty == Decimal("0.2")
    assert snapshot.exec_type == "Trade"
    assert snapshot.order_type == "Market"
    assert snapshot.leverage == 10
    assert snapshot.raw == {"part": "last"}


def test_closed_pnl_snapshot_accepts_original_five_positional_arguments() -> None:
    snapshot = ClosedPnlSnapshot("close-1", Decimal("1"), None, None, None)

    assert snapshot.order_id == "close-1"
    assert snapshot.raw is None


async def test_closed_pnl_page_clamps_old_since_to_recent_seven_day_window(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    exchange = _mock_exchange(monkeypatch)
    await BybitFuturesProvider().fetch_closed_pnl_page(
        credentials,
        "BTC/USDT",
        since=datetime.now(UTC) - timedelta(days=8),
    )

    kwargs = exchange.fetch_positions_history.await_args.kwargs
    assert kwargs["params"]["until"] - kwargs["since"] == _CLOSED_PNL_MAX_WINDOW_MS


async def test_fetch_closed_pnl_rows_passes_none_for_all_symbols(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    exchange = _mock_exchange(monkeypatch)
    await BybitFuturesProvider()._fetch_closed_pnl_rows(
        credentials,
        None,
        since_ms=100,
        until_ms=200,
    )

    exchange.fetch_positions_history.assert_awaited_once_with(
        None,
        since=100,
        limit=100,
        params={"until": 200},
    )


async def test_closed_order_meta_uses_closed_orders_and_normalizes_blank_fields(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    exchange = _mock_exchange(monkeypatch)
    exchange.fetch_closed_orders = AsyncMock(
        return_value=[
            {
                "timestamp": 200,
                "info": {
                    "orderId": "close-1",
                    "createType": "",
                    "stopOrderType": "StopLoss",
                    "orderLinkId": "",
                    "updatedTime": "200",
                },
            }
        ]
    )

    meta = await BybitFuturesProvider().fetch_closed_order_meta(
        credentials,
        None,
        start_ms=100,
        end_ms=200,
    )

    assert meta["close-1"].create_type is None
    assert meta["close-1"].stop_order_type == "StopLoss"
    assert meta["close-1"].order_link_id is None
    exchange.fetch_closed_orders.assert_awaited_once_with(
        None,
        since=100,
        limit=100,
        params={"until": 200},
    )
    exchange.fetch_orders.assert_not_called()

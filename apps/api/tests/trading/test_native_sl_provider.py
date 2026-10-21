"""공식 V5 부모 응답의 제한된 복구. CCXT는 대역이며 네트워크를 쓰지 않는다."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.exceptions import ProviderError
from src.trading.providers import BybitFuturesProvider, Credentials


@pytest.fixture
def exchange(monkeypatch):
    mock = MagicMock()
    empty = {"retCode": 0, "result": {"category": "linear", "list": [], "nextPageCursor": ""}}
    mock.privateGetV5OrderRealtime = AsyncMock(return_value=empty)
    mock.privateGetV5OrderHistory = AsyncMock(return_value=empty)
    mock.close = AsyncMock()
    monkeypatch.setattr("src.trading.providers.ccxt_async.bybit", lambda _: mock)
    return mock


async def test_bounded_native_history_uses_response_parent_not_query_filter(exchange):
    row = {
        "parentOrderLinkId": "parent",
        "orderId": "child",
        "symbol": "BTCUSDT",
        "stopOrderType": "StopLoss",
    }
    exchange.privateGetV5OrderHistory.side_effect = [
        {"retCode": 0, "result": {"category": "linear", "list": [row], "nextPageCursor": "next"}},
        {"retCode": 0, "result": {"category": "linear", "list": [], "nextPageCursor": ""}},
    ]
    result = await BybitFuturesProvider().fetch_attached_sl_orders(
        Credentials("fake", "fake"), "BTC/USDT:USDT", since=datetime.now(UTC)
    )
    assert result == [{**row, "category": "linear"}]
    requests = [c.args[0] for c in exchange.privateGetV5OrderHistory.await_args_list]
    assert requests[0]["category"] == "linear" and requests[0]["symbol"] == "BTCUSDT"
    assert requests[0]["limit"] == 50 and "parentOrderLinkId" not in requests[0]
    assert requests[1]["cursor"] == "next"
    exchange.close.assert_awaited_once()
    exchange.create_order.assert_not_called()


@pytest.mark.parametrize(
    "result",
    [
        {"category": "spot", "list": [], "nextPageCursor": ""},
        {"category": "linear", "list": [None], "nextPageCursor": ""},
        {"category": "linear", "list": []},
        {"category": "linear", "list": [], "nextPageCursor": None},
        {"category": "linear", "list": [], "nextPageCursor": 0},
        {
            "category": "linear",
            "list": [{"parentOrderLinkId": "x", "stopOrderType": "StopLoss", "symbol": "ETHUSDT"}],
            "nextPageCursor": "",
        },
    ],
)
async def test_native_history_rejects_malformed_or_foreign_scope(exchange, result):
    exchange.privateGetV5OrderRealtime.return_value = {"retCode": 0, "result": result}
    with pytest.raises(ProviderError):
        await BybitFuturesProvider().fetch_attached_sl_orders(
            Credentials("fake", "fake"), "BTCUSDT", since=datetime.now(UTC)
        )
    exchange.close.assert_awaited_once()
    exchange.privateGetV5OrderHistory.assert_not_awaited()


@pytest.mark.parametrize("cursors", [["same", "same"], ["first", "second"]])
async def test_native_history_cursor_repeat_or_budget_never_confirms_partial_results(
    exchange, cursors
):
    exchange.privateGetV5OrderRealtime.side_effect = [
        {"retCode": 0, "result": {"category": "linear", "list": [], "nextPageCursor": cursor}}
        for cursor in cursors
    ]
    with pytest.raises(ProviderError, match=r"cursor repeated|page budget"):
        await BybitFuturesProvider().fetch_attached_sl_orders(
            Credentials("fake", "fake"), "BTCUSDT", since=datetime.now(UTC)
        )
    assert exchange.privateGetV5OrderRealtime.await_count == 2
    exchange.privateGetV5OrderHistory.assert_not_awaited()
    exchange.close.assert_awaited_once()

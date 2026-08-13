# Bybit 조건부 진입 주문 조회를 검증한다.
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.providers import BybitFuturesProvider, Credentials


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(api_key="test-key", api_secret="test-secret")


def _conditional_order(
    order_id: str,
    *,
    reduce_only: bool | str,
    stop_order_type: str,
    client_order_id: str | None = None,
    order_link_id: str | None = None,
) -> dict[str, object]:
    order: dict[str, object] = {
        "id": order_id,
        "side": "Sell",
        "amount": "1",
        "info": {
            "stopOrderType": stop_order_type,
            "reduceOnly": reduce_only,
        },
    }
    if client_order_id is not None:
        order["clientOrderId"] = client_order_id
    if order_link_id is not None:
        order["info"] = {
            "stopOrderType": stop_order_type,
            "reduceOnly": reduce_only,
            "orderLinkId": order_link_id,
        }
    return order


def _bybit_mock(
    monkeypatch: pytest.MonkeyPatch, *responses: list[dict[str, object]]
) -> MagicMock:
    import ccxt.async_support as ccxt_async

    exchange = MagicMock()
    exchange.fetch_open_orders = AsyncMock(side_effect=responses)
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))
    return exchange


async def test_fetch_open_conditional_orders_defaults_to_reduce_only_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    exchange = _bybit_mock(
        monkeypatch,
        [
            _conditional_order("tp", reduce_only=True, stop_order_type="TakeProfit"),
            _conditional_order("entry-string", reduce_only="false", stop_order_type="Stop"),
        ],
        [
            _conditional_order("tp", reduce_only=True, stop_order_type="TakeProfit"),
            _conditional_order("entry-bool", reduce_only=False, stop_order_type="Stop"),
        ],
    )

    snapshots = await BybitFuturesProvider().fetch_open_conditional_orders(
        credentials, "BTC/USDT"
    )

    assert [(snapshot.order_id, snapshot.reduce_only) for snapshot in snapshots] == [("tp", True)]
    assert exchange.fetch_open_orders.await_args_list[0].args == ("BTC/USDT:USDT",)
    assert exchange.fetch_open_orders.await_args_list[0].kwargs == {
        "params": {"category": "linear", "paginate": True}
    }
    assert exchange.fetch_open_orders.await_args_list[1].kwargs == {
        "params": {"category": "linear", "trigger": True, "paginate": True}
    }


async def test_fetch_open_conditional_orders_includes_entry_when_filter_is_none(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    _bybit_mock(
        monkeypatch,
        [
            _conditional_order(
                "entry",
                reduce_only=False,
                stop_order_type="Stop",
                client_order_id="client-entry",
                order_link_id="raw-entry",
            )
        ],
        [],
    )

    snapshots = await BybitFuturesProvider().fetch_open_conditional_orders(
        credentials, "BTC/USDT", reduce_only=None
    )

    assert [(snapshot.order_id, snapshot.kind, snapshot.reduce_only) for snapshot in snapshots] == [
        ("entry", "other", False)
    ]
    assert snapshots[0].order_link_id == "client-entry"


async def test_fetch_open_conditional_orders_false_returns_only_entries(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    _bybit_mock(
        monkeypatch,
        [
            _conditional_order("tp", reduce_only=True, stop_order_type="TakeProfit"),
            _conditional_order("entry", reduce_only=False, stop_order_type="Stop"),
        ],
        [],
    )

    snapshots = await BybitFuturesProvider().fetch_open_conditional_orders(
        credentials, "BTC/USDT", reduce_only=False
    )

    assert [(snapshot.order_id, snapshot.reduce_only) for snapshot in snapshots] == [
        ("entry", False)
    ]


async def test_fetch_open_conditional_orders_falls_back_to_order_link_id(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    _bybit_mock(
        monkeypatch,
        [
            _conditional_order(
                "entry", reduce_only=False, stop_order_type="Stop", order_link_id="raw-entry"
            )
        ],
        [],
    )

    snapshots = await BybitFuturesProvider().fetch_open_conditional_orders(
        credentials, "BTC/USDT", reduce_only=None
    )

    assert snapshots[0].order_link_id == "raw-entry"


@pytest.mark.asyncio
async def test_string_reduce_only_false_is_not_treated_as_true(
    monkeypatch: pytest.MonkeyPatch, credentials: Credentials
) -> None:
    """거래소가 `reduceOnly` 를 문자열로 줄 때 `bool("false") is True` 함정을 피한다.

    문자열 "false" 를 그대로 bool() 하면 True 가 되어 진입 stop 이 reduce-only 로 분류되고,
    코크핏에 **없는 손절이 있는 것처럼** 보인다.
    """
    exchange = _bybit_mock(
        monkeypatch,
        [_conditional_order("entry", reduce_only="false", stop_order_type="Stop")],
        [],
    )
    provider = BybitFuturesProvider()

    default_only = await provider.fetch_open_conditional_orders(credentials, "BTC/USDT")
    exchange.fetch_open_orders.side_effect = [
        [_conditional_order("entry", reduce_only="false", stop_order_type="Stop")],
        [],
    ]
    unfiltered = await provider.fetch_open_conditional_orders(
        credentials, "BTC/USDT", reduce_only=None
    )

    assert default_only == []
    assert [(s.order_id, s.reduce_only) for s in unfiltered] == [("entry", False)]

"""BybitFuturesProvider의 LastPrice 우선 ticker 조회를 검증한다."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import ccxt.async_support as ccxt_async
import pytest

from src.trading.providers import BybitFuturesProvider, Credentials


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(api_key="test-key", api_secret="test-secret")


@pytest.fixture
def ccxt_exchange(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    exchange = MagicMock()
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))
    return exchange


async def test_last_price_prefers_last_over_mark(
    credentials: Credentials,
    ccxt_exchange: MagicMock,
) -> None:
    ccxt_exchange.fetch_ticker = AsyncMock(
        return_value={"mark": "101", "last": "100", "close": "99"}
    )

    price = await BybitFuturesProvider().fetch_last_price(credentials, "BTC/USDT")

    assert price == Decimal("100")
    ccxt_exchange.close.assert_awaited_once()


async def test_ticker_is_fetched_with_linear_symbol(
    credentials: Credentials,
    ccxt_exchange: MagicMock,
) -> None:
    ccxt_exchange.fetch_ticker = AsyncMock(return_value={"last": "100"})

    await BybitFuturesProvider().fetch_last_price(credentials, "BTC/USDT")

    ccxt_exchange.fetch_ticker.assert_awaited_once_with("BTC/USDT:USDT")


async def test_mark_price_reads_info_mark_price(
    credentials: Credentials,
    ccxt_exchange: MagicMock,
) -> None:
    ccxt_exchange.fetch_ticker = AsyncMock(
        return_value={"info": {"markPrice": "101"}, "last": "100", "close": "99"}
    )

    price = await BybitFuturesProvider().fetch_mark_price(credentials, "BTC/USDT")

    assert price == Decimal("101")


async def test_last_price_does_not_use_dead_mark_key(
    credentials: Credentials,
    ccxt_exchange: MagicMock,
) -> None:
    ccxt_exchange.fetch_ticker = AsyncMock(return_value={"mark": "101", "close": "99"})

    price = await BybitFuturesProvider().fetch_last_price(credentials, "BTC/USDT")

    assert price == Decimal("99")


async def test_last_price_falls_back_to_close(
    credentials: Credentials,
    ccxt_exchange: MagicMock,
) -> None:
    ccxt_exchange.fetch_ticker = AsyncMock(return_value={"mark": "101", "close": "99"})

    price = await BybitFuturesProvider().fetch_last_price(credentials, "BTC/USDT")

    assert price == Decimal("99")


async def test_last_price_returns_none_on_provider_error(
    credentials: Credentials,
    ccxt_exchange: MagicMock,
) -> None:
    ccxt_exchange.fetch_ticker = AsyncMock(side_effect=RuntimeError("network unavailable"))

    price = await BybitFuturesProvider().fetch_last_price(credentials, "BTC/USDT")

    assert price is None
    ccxt_exchange.close.assert_awaited_once()

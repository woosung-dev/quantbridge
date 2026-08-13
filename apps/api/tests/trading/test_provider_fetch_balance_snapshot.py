# Bybit USDT wallet balance snapshot 정규화를 검증한다.
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="test-key", api_secret="test-secret")


@pytest.fixture
def ccxt_mock(monkeypatch):
    mock_exchange = MagicMock()
    mock_exchange.fetch_balance = AsyncMock()
    mock_exchange.close = AsyncMock()
    mock_bybit = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit)
    return mock_exchange


async def test_fetch_usdt_balance_snapshot_extracts_total_and_free(credentials, ccxt_mock):
    from src.trading.providers import BybitFuturesProvider

    ccxt_mock.fetch_balance.return_value = {
        "USDT": {"total": "1334.5", "free": "1234.5", "used": "100"}
    }

    snapshot = await BybitFuturesProvider().fetch_usdt_balance_snapshot(credentials)

    assert snapshot.total == Decimal("1334.5")
    assert snapshot.free == Decimal("1234.5")
    ccxt_mock.close.assert_awaited_once()


async def test_fetch_usdt_balance_snapshot_returns_none_when_usdt_missing(credentials, ccxt_mock):
    from src.trading.providers import BybitFuturesProvider

    ccxt_mock.fetch_balance.return_value = {"BTC": {"total": "1", "free": "1"}}

    snapshot = await BybitFuturesProvider().fetch_usdt_balance_snapshot(credentials)

    assert snapshot.total is None
    assert snapshot.free is None


async def test_fetch_usdt_balance_snapshot_ignores_non_finite_and_garbage_values(
    credentials, ccxt_mock
):
    from src.trading.providers import BybitFuturesProvider

    ccxt_mock.fetch_balance.return_value = {"USDT": {"total": "NaN", "free": "not-a-number"}}

    snapshot = await BybitFuturesProvider().fetch_usdt_balance_snapshot(credentials)

    assert snapshot.total is None
    assert snapshot.free is None


async def test_fetch_usdt_balance_snapshot_wraps_ccxt_error_and_closes(credentials, ccxt_mock):
    import ccxt.async_support as ccxt_async

    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    ccxt_mock.fetch_balance.side_effect = ccxt_async.NetworkError("connection timeout")

    with pytest.raises(ProviderError, match="NetworkError"):
        await BybitFuturesProvider().fetch_usdt_balance_snapshot(credentials)

    ccxt_mock.close.assert_awaited_once()

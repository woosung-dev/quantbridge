# STEP B — BybitFuturesProvider.fetch_position (stale-position 가드용 현재 포지션 조회).
"""place_trailing_stop 가 체결 후 trailing 부착 전 현재 포지션을 확인(stale/flip/flat 차단).
ccxt fetch_positions([symbol]) → 정규화 PositionInfo(size>0, side) 또는 None(무포지션).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="test-key", api_secret="test-secret")


def _bybit_mock(monkeypatch, positions):
    mock_exchange = MagicMock()
    mock_exchange.fetch_positions = AsyncMock(return_value=positions)
    mock_exchange.close = AsyncMock()
    mock_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_cls)
    return mock_exchange


async def test_fetch_position_long(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(monkeypatch, [{"contracts": 0.001, "side": "long", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None
    assert pos.size == Decimal("0.001")
    assert pos.side == "long"


async def test_fetch_position_none_when_flat(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    # size 0 포지션만 → None.
    _bybit_mock(monkeypatch, [{"contracts": 0.0, "side": "long", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is None


async def test_fetch_position_none_when_empty(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(monkeypatch, [])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is None


async def test_fetch_position_short(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    m = _bybit_mock(monkeypatch, [{"contracts": 0.5, "side": "short", "info": {}}])
    pos = await BybitFuturesProvider().fetch_position(credentials, "BTC/USDT")
    assert pos is not None and pos.side == "short" and pos.size == Decimal("0.5")
    # linear symbol 정규화 + 정리.
    m.fetch_positions.assert_awaited_once_with(["BTC/USDT:USDT"])
    m.close.assert_awaited()

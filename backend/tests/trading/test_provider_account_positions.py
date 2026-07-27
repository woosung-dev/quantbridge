# BL-498 — 계정 전체 포지션 조회와 심볼 역정규화를 검증한다.
"""심볼 인자 없는 `fetch_positions()` 로 계정에 남은 linear 포지션을 한 번에 읽는다.

활성 세션이 0건이면 물어볼 심볼조차 없으므로, 심볼 스코프 조회로는 잔여 노출을
찾을 수 없다는 것이 BL-498 의 구조적 원인이다.
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
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=mock_exchange))
    return mock_exchange


def _ccxt_position(symbol: str, *, contracts: float = 0.03, side: str = "short"):
    return {
        "symbol": symbol,
        "contracts": contracts,
        "side": side,
        "entryPrice": "65340.2",
        "markPrice": "65100.0",
        "unrealizedPnl": "7.22",
        "liquidationPrice": None,
        "leverage": "10",
        "takeProfitPrice": None,
        "stopLossPrice": None,
        "info": {"positionIdx": "0"},
    }


async def test_fetch_all_open_positions_asks_without_a_symbol(monkeypatch, credentials):
    """★심볼 인자를 주지 않아야 계정 전체가 온다. 주면 BL-498 이 그대로 남는다."""
    from src.trading.providers import BybitFuturesProvider

    exchange = _bybit_mock(monkeypatch, [_ccxt_position("BTC/USDT:USDT")])

    rows, truncated = await BybitFuturesProvider().fetch_all_open_positions(credentials)

    exchange.fetch_positions.assert_awaited_once_with()
    assert truncated is False
    assert [symbol for symbol, _ in rows] == ["BTC/USDT"]
    assert rows[0][1].size == Decimal("0.03")
    assert rows[0][1].side == "short"
    assert rows[0][1].position_idx == 0


async def test_flat_legs_are_dropped(monkeypatch, credentials):
    from src.trading.providers import BybitFuturesProvider

    _bybit_mock(
        monkeypatch,
        [
            _ccxt_position("BTC/USDT:USDT", contracts=0.0),
            _ccxt_position("ETH/USDT:USDT", contracts=1.5, side="long"),
        ],
    )

    rows, _ = await BybitFuturesProvider().fetch_all_open_positions(credentials)

    assert [symbol for symbol, _ in rows] == ["ETH/USDT"]


async def test_missing_symbol_is_rejected_not_guessed(monkeypatch, credentials):
    """★심볼이 없으면 청산 귀속을 정할 수 없다. 추측하지 말고 실패한다."""
    from src.trading.providers import BybitFuturesProvider, ProviderError

    position = _ccxt_position("BTC/USDT:USDT")
    del position["symbol"]
    _bybit_mock(monkeypatch, [position])

    with pytest.raises(ProviderError):
        await BybitFuturesProvider().fetch_all_open_positions(credentials)


def test_linear_symbol_round_trip_is_identity():
    """★USDT-settled linear 은 canonical -> bybit -> canonical 이 항등이어야 한다."""
    from src.trading.providers import _from_bybit_linear_symbol, _to_bybit_linear_symbol

    for canonical in ("BTC/USDT", "ETH/USDT", "SOL/USDT"):
        assert _from_bybit_linear_symbol(_to_bybit_linear_symbol(canonical)) == canonical


def test_inverse_symbol_is_left_alone():
    """★역변환이 inverse 를 뭉개면 서로 다른 시장이 같은 문자열이 된다.

    `BTC/USD:BTC` 를 `BTC/USD` 로 되돌리면 다시 `BTC/USD:USD` 가 되어 왕복이 깨진다.
    settle 이 quote 와 다르면 원문을 그대로 둔다.
    """
    from src.trading.providers import _from_bybit_linear_symbol

    assert _from_bybit_linear_symbol("BTC/USD:BTC") == "BTC/USD:BTC"


def test_already_canonical_symbol_passes_through():
    from src.trading.providers import _from_bybit_linear_symbol

    assert _from_bybit_linear_symbol("BTC/USDT") == "BTC/USDT"
    assert _from_bybit_linear_symbol("BTCUSDT") == "BTCUSDT"


async def test_next_page_cursor_is_surfaced_not_swallowed(monkeypatch, credentials):
    """★ccxt 는 한 페이지(limit 200)만 부르고 커서를 첫 항목에 도장만 찍는다.

    조용히 자르면 화면이 "이게 전부" 라고 거짓말한다 — 잔여 노출 관리 표에서 그건
    BL-498 의 증상 그 자체다.
    """
    from src.trading.providers import BybitFuturesProvider

    position = _ccxt_position("BTC/USDT:USDT")
    position["info"]["nextPageCursor"] = "cursor%3A1"
    _bybit_mock(monkeypatch, [position])

    rows, truncated = await BybitFuturesProvider().fetch_all_open_positions(credentials)

    assert truncated is True
    assert len(rows) == 1

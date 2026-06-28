# STEP B — BybitFuturesProvider.set_trading_stop (포지션 trailing-stop placement) param shape 검증.
"""트레일링은 별도 주문이 아니라 포지션 속성. ccxt 4.5.49 가 trailingStop param 이 붙은
create_order 를 Bybit trading-stop 엔드포인트(privatePostV5PositionTradingStop)로 라우팅.

검증 사실(bybit.py 4100-4116):
- isTrailingOrder → request['qty'] 미설정(side/qty 는 ccxt 시그니처용, Bybit 미전송).
- request['trailingStop'] = trailingAmount. triggerDirection 분기 미도달(불필요).
- trailingTriggerPrice → activePrice (옵션).
- reduceOnly/triggerBy/triggerDirection 는 이 엔드포인트 no-op → 미전송(speculative 금지).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="test-key", api_secret="test-secret")


@pytest.fixture
def bybit_mock(monkeypatch):
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={"id": "ts-1", "average": None, "status": "closed"}
    )
    mock_exchange.close = AsyncMock()
    mock_exchange.load_markets = AsyncMock(return_value={})
    mock_exchange.amount_to_precision = MagicMock(side_effect=lambda s, a: str(a))
    mock_exchange.price_to_precision = MagicMock(side_effect=lambda s, p: str(p))
    mock_exchange.set_margin_mode = AsyncMock()
    mock_exchange.set_leverage = AsyncMock()
    mock_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_cls)
    return mock_exchange


async def test_set_trading_stop_basic_shape(credentials, bybit_mock):
    """distance 만 → params {"trailingStop": str(distance)}, linear market, side/qty 전달(드롭됨)."""
    from src.trading.models import OrderSide
    from src.trading.providers import BybitFuturesProvider

    await BybitFuturesProvider().set_trading_stop(
        credentials,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        qty=Decimal("0.001"),
        distance=Decimal("150.5"),
    )
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT",
        "market",
        "sell",
        "0.001",
        None,
        {"trailingStop": "150.5"},
    )


async def test_set_trading_stop_no_speculative_params(credentials, bybit_mock):
    """reduceOnly/triggerBy/triggerDirection 미전송(이 엔드포인트 no-op)."""
    from src.trading.models import OrderSide
    from src.trading.providers import BybitFuturesProvider

    await BybitFuturesProvider().set_trading_stop(
        credentials,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        qty=Decimal("0.002"),
        distance=Decimal("80"),
    )
    params = bybit_mock.create_order.call_args.args[5]
    assert "reduceOnly" not in params
    assert "triggerBy" not in params
    assert "triggerDirection" not in params
    assert params == {"trailingStop": "80"}


async def test_set_trading_stop_accepts_empty_result_no_id(credentials, bybit_mock):
    """codex P1 — Bybit trading-stop 엔드포인트 성공 = 빈 result(orderId 없음, V5 docs).

    id 부재를 malformed 로 오판하면 성공 placement 를 retry → false UNPROTECTED alert
    (money-path bug). 빈 dict 수용 = 예외 없음.
    """
    from src.trading.models import OrderSide
    from src.trading.providers import BybitFuturesProvider

    bybit_mock.create_order = AsyncMock(return_value={})  # 실제 Bybit trading-stop 응답
    res = await BybitFuturesProvider().set_trading_stop(
        credentials,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        qty=Decimal("0.001"),
        distance=Decimal("150.5"),
    )
    assert res == {}  # 예외 없이 수용
    bybit_mock.close.assert_awaited()


async def test_set_trading_stop_wraps_ccxt_error(credentials, bybit_mock):
    """ccxt BaseError → ProviderError 래핑(money-path 분류용)."""
    import ccxt.async_support as ccxt_async

    from src.trading.models import OrderSide
    from src.trading.providers import BybitFuturesProvider, ProviderError

    bybit_mock.create_order = AsyncMock(
        side_effect=ccxt_async.InvalidOrder("110017 position is zero")
    )

    with pytest.raises(ProviderError) as exc:
        await BybitFuturesProvider().set_trading_stop(
            credentials,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            qty=Decimal("0.001"),
            distance=Decimal("150.5"),
        )
    assert "110017" in str(exc.value)
    bybit_mock.close.assert_awaited()


async def test_set_trading_stop_rejects_unvalidated_ccxt(credentials, bybit_mock, monkeypatch):
    """kill-switch 2차방어 — 미검증 ccxt 버전이면 발주 전 TrailingContractError raise(non-retry)."""
    import ccxt.async_support as ccxt_async

    from src.trading.exceptions import TrailingContractError
    from src.trading.models import OrderSide
    from src.trading.providers import BybitFuturesProvider

    monkeypatch.setattr(ccxt_async, "__version__", "9.9.9", raising=False)
    with pytest.raises(TrailingContractError) as ei:
        await BybitFuturesProvider().set_trading_stop(
            credentials,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            qty=Decimal("0.001"),
            distance=Decimal("150.5"),
        )
    assert ei.value.reason == "ccxt_unvalidated"
    bybit_mock.create_order.assert_not_awaited()  # 잘못될 수 있는 주문 미발주

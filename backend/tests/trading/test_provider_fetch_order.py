"""Sprint 15 Phase A.1 — provider.fetch_order interface + 4 provider 구현.

ExchangeProvider Protocol 에 fetch_order 추가. submitted watchdog (BL-001) 의
terminal 전이 evidence 확보. CCXT fetch_order(id, symbol) wrap.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="fetch-test", api_secret="fetch-secret")


@pytest.fixture
def credentials_okx():
    from src.trading.providers import Credentials

    return Credentials(
        api_key="okx-fetch", api_secret="okx-secret", passphrase="okx-pass"
    )


# -------------------------------------------------------------------------
# OrderStatusFetch dataclass + helper
# -------------------------------------------------------------------------


def test_order_status_fetch_dataclass_frozen():
    """OrderStatusFetch is frozen + slots — credentials 가 raw 안 들어가지 않게 contract."""
    from src.trading.providers import OrderStatusFetch

    status = OrderStatusFetch(
        exchange_order_id="ex-1",
        status="submitted",
        filled_price=None,
        filled_quantity=None,
        raw={"id": "ex-1"},
    )
    assert status.exchange_order_id == "ex-1"
    assert status.status == "submitted"
    with pytest.raises(Exception):  # frozen → FrozenInstanceError
        status.status = "filled"  # type: ignore[misc]


def test_map_ccxt_status_for_fetch_four_states():
    """fetch 용 helper: cancelled 별도 분기. closed/filled → filled, canceled → cancelled,
    rejected/expired → rejected, 그 외 → submitted."""
    from src.trading.providers import _map_ccxt_status_for_fetch

    assert _map_ccxt_status_for_fetch("closed") == "filled"
    assert _map_ccxt_status_for_fetch("filled") == "filled"
    assert _map_ccxt_status_for_fetch("canceled") == "cancelled"
    assert _map_ccxt_status_for_fetch("cancelled") == "cancelled"
    assert _map_ccxt_status_for_fetch("rejected") == "rejected"
    assert _map_ccxt_status_for_fetch("expired") == "rejected"
    assert _map_ccxt_status_for_fetch("open") == "submitted"
    assert _map_ccxt_status_for_fetch("pending") == "submitted"
    assert _map_ccxt_status_for_fetch(None) == "submitted"


# -------------------------------------------------------------------------
# FixtureExchangeProvider.fetch_order (deterministic, no CCXT)
# -------------------------------------------------------------------------


async def test_fixture_provider_fetch_order_default_filled(credentials):
    """FixtureExchangeProvider.fetch_order — 기본 응답 filled."""
    from src.trading.providers import FixtureExchangeProvider

    provider = FixtureExchangeProvider()
    result = await provider.fetch_order(credentials, "fixture-1", "BTC/USDT")
    assert result.exchange_order_id == "fixture-1"
    assert result.status == "filled"
    assert result.filled_price == Decimal("50000.00")


async def test_fixture_provider_fetch_order_configurable_status(credentials):
    """FixtureExchangeProvider — fetch_status_override 로 status 조작 가능."""
    from src.trading.providers import FixtureExchangeProvider

    provider = FixtureExchangeProvider(fetch_status_override="cancelled")
    result = await provider.fetch_order(credentials, "fix-2", "BTC/USDT")
    assert result.status == "cancelled"

    provider2 = FixtureExchangeProvider(fetch_status_override="submitted")
    result2 = await provider2.fetch_order(credentials, "fix-3", "BTC/USDT")
    assert result2.status == "submitted"


# -------------------------------------------------------------------------
# BybitDemoProvider.fetch_order
# -------------------------------------------------------------------------


@pytest.fixture
def bybit_fetch_mock(monkeypatch):
    """ccxt.async_support.bybit를 AsyncMock으로 교체 — fetch_order 시나리오."""
    mock_exchange = MagicMock()
    mock_exchange.fetch_order = AsyncMock(
        return_value={
            "id": "bybit-order-99",
            "average": 50123.45,
            "amount": 0.001,
            "filled": 0.001,
            "status": "closed",
            "symbol": "BTC/USDT",
        }
    )
    mock_exchange.close = AsyncMock()
    mock_bybit_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


async def test_bybit_demo_fetch_order_uses_credentials(credentials, bybit_fetch_mock):
    mock_exchange, mock_bybit_cls = bybit_fetch_mock
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    result = await provider.fetch_order(credentials, "bybit-order-99", "BTC/USDT")

    # CCXT 인스턴스가 credentials 로 생성됐는지
    mock_bybit_cls.assert_called_once()
    call_kwargs = mock_bybit_cls.call_args.args[0]
    assert call_kwargs["apiKey"] == "fetch-test"
    assert call_kwargs["secret"] == "fetch-secret"
    assert call_kwargs["options"]["defaultType"] == "spot"
    mock_exchange.enable_demo_trading.assert_called_once_with(True)

    # fetch_order 호출 인자 (BL-404: acknowledged 의무 — 아래 전용 테스트 참조)
    mock_exchange.fetch_order.assert_awaited_once_with(
        "bybit-order-99", "BTC/USDT", params={"acknowledged": True}
    )

    # 응답 매핑
    assert result.exchange_order_id == "bybit-order-99"
    assert result.status == "filled"
    assert result.filled_price == Decimal("50123.45")
    assert result.filled_quantity == Decimal("0.001")

    # 호출 후 close()
    mock_exchange.close.assert_awaited_once()


async def test_bybit_demo_fetch_order_open_status_maps_submitted(
    credentials, bybit_fetch_mock
):
    mock_exchange, _ = bybit_fetch_mock
    mock_exchange.fetch_order = AsyncMock(
        return_value={
            "id": "bybit-99",
            "average": None,
            "amount": 0.001,
            "filled": 0,
            "status": "open",
            "symbol": "BTC/USDT",
        }
    )
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    result = await provider.fetch_order(credentials, "bybit-99", "BTC/USDT")
    assert result.status == "submitted"
    assert result.filled_price is None


async def test_bybit_demo_fetch_order_canceled_maps_cancelled(
    credentials, bybit_fetch_mock
):
    mock_exchange, _ = bybit_fetch_mock
    mock_exchange.fetch_order = AsyncMock(
        return_value={
            "id": "bybit-99",
            "average": None,
            "filled": 0,
            "status": "canceled",
            "symbol": "BTC/USDT",
        }
    )
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    result = await provider.fetch_order(credentials, "bybit-99", "BTC/USDT")
    assert result.status == "cancelled"


# -------------------------------------------------------------------------
# BybitFuturesProvider.fetch_order — defaultType=linear
# -------------------------------------------------------------------------


async def test_bybit_futures_fetch_order_uses_linear(credentials, bybit_fetch_mock):
    mock_exchange, mock_bybit_cls = bybit_fetch_mock
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    result = await provider.fetch_order(credentials, "bybit-fut-1", "BTC/USDT:USDT")

    mock_bybit_cls.assert_called_once()
    call_kwargs = mock_bybit_cls.call_args.args[0]
    assert call_kwargs["options"]["defaultType"] == "linear"
    mock_exchange.fetch_order.assert_awaited_once_with(
        "bybit-fut-1", "BTC/USDT:USDT", params={"acknowledged": True}
    )
    assert result.exchange_order_id == "bybit-fut-1"
    assert result.status == "filled"
    mock_exchange.close.assert_awaited_once()


async def test_bybit_fetch_order_passes_acknowledged_param(
    credentials, bybit_fetch_mock
):
    """BL-404 — ccxt bybit fetchOrder 는 params["acknowledged"]=True 없이
    ArgumentsRequired 를 raise (last-500-orders 제약 인지 게이트). 누락 시
    watchdog fetch 전면 실패 → 라이브 주문 submitted 영구 고착 (2026-07-05
    dogfood 실측). demo/futures 공유 impl 이 param 을 항상 전달해야 한다."""
    mock_exchange, _ = bybit_fetch_mock
    from src.trading.providers import BybitDemoProvider, BybitFuturesProvider

    await BybitDemoProvider().fetch_order(credentials, "ord-1", "BTC/USDT")
    demo_call = mock_exchange.fetch_order.await_args
    assert demo_call.kwargs.get("params", {}).get("acknowledged") is True

    mock_exchange.fetch_order.reset_mock()
    await BybitFuturesProvider().fetch_order(credentials, "ord-2", "BTC/USDT:USDT")
    fut_call = mock_exchange.fetch_order.await_args
    assert fut_call.kwargs.get("params", {}).get("acknowledged") is True


async def test_bybit_futures_fetch_order_normalizes_spot_symbol(
    credentials, bybit_fetch_mock
):
    """BL-404 — watchdog 이 DB order.symbol(spot 포맷 `BTC/USDT`)을 그대로 전달하면
    ccxt 가 category=spot 으로 조회해 linear 주문이 OrderNotFound (2026-07-05
    실 demo 대조: `BTC/USDT:USDT`=OK / `BTC/USDT`=NotFound). create_order 와
    동일하게 `_to_bybit_linear_symbol` 정규화를 거쳐야 한다."""
    mock_exchange, _ = bybit_fetch_mock
    from src.trading.providers import BybitFuturesProvider

    await BybitFuturesProvider().fetch_order(credentials, "ord-3", "BTC/USDT")
    call = mock_exchange.fetch_order.await_args
    assert call.args[1] == "BTC/USDT:USDT"


# -------------------------------------------------------------------------
# OkxDemoProvider.fetch_order — passphrase + sandbox
# -------------------------------------------------------------------------


@pytest.fixture
def okx_fetch_mock(monkeypatch):
    mock_exchange = MagicMock()
    mock_exchange.fetch_order = AsyncMock(
        return_value={
            "id": "okx-order-7",
            "average": 51000.0,
            "amount": 0.005,
            "filled": 0.005,
            "status": "closed",
            "symbol": "BTC/USDT",
        }
    )
    mock_exchange.close = AsyncMock()
    mock_okx_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "okx", mock_okx_cls)
    return mock_exchange, mock_okx_cls


async def test_okx_demo_fetch_order_uses_passphrase(credentials_okx, okx_fetch_mock):
    mock_exchange, mock_okx_cls = okx_fetch_mock
    from src.trading.providers import OkxDemoProvider

    provider = OkxDemoProvider()
    result = await provider.fetch_order(credentials_okx, "okx-order-7", "BTC/USDT")

    mock_okx_cls.assert_called_once()
    call_kwargs = mock_okx_cls.call_args.args[0]
    assert call_kwargs["password"] == "okx-pass"
    mock_exchange.set_sandbox_mode.assert_called_once_with(True)
    mock_exchange.fetch_order.assert_awaited_once_with("okx-order-7", "BTC/USDT")
    assert result.status == "filled"
    assert result.filled_price == Decimal("51000.0")
    mock_exchange.close.assert_awaited_once()


async def test_okx_demo_fetch_order_rejects_missing_passphrase(okx_fetch_mock):
    """OKX 는 passphrase 없으면 ProviderError fast-fail (계약 위반 차단)."""
    from src.trading.exceptions import ProviderError
    from src.trading.providers import Credentials, OkxDemoProvider

    provider = OkxDemoProvider()
    creds = Credentials(api_key="x", api_secret="y")  # passphrase=None
    with pytest.raises(ProviderError):
        await provider.fetch_order(creds, "okx-1", "BTC/USDT")

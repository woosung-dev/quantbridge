"""OkxDemoProvider — CCXT async_support monkeypatch (no network).

Sprint 7d. Bybit demo pattern 답습 + OKX 특이사항:
- ``password`` (CCXT 파라미터명) = passphrase
- ``set_sandbox_mode(True)`` 로 demo 라우팅 (Bybit의 ``testnet`` 옵션과 다름)
- options.defaultType = "spot" (Sprint 7d는 spot only)
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def creds_with_passphrase():
    from src.trading.providers import Credentials

    return Credentials(
        api_key="okx-key", api_secret="okx-secret", passphrase="okx-pass"
    )


@pytest.fixture
def order_submit():
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit

    return OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
        leverage=None,
        margin_mode=None,
    )


@pytest.fixture
def ccxt_okx_mock(monkeypatch):
    """ccxt.async_support.okx → AsyncMock."""
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={
            "id": "okx-order-7",
            "average": 50421.50,
            "status": "closed",
            "symbol": "BTC/USDT",
        }
    )
    mock_exchange.cancel_order = AsyncMock(return_value={})
    mock_exchange.close = AsyncMock()
    mock_exchange.set_sandbox_mode = MagicMock()

    mock_okx_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "okx", mock_okx_cls)
    return mock_exchange, mock_okx_cls


async def test_okx_demo_uses_credentials_with_passphrase(
    creds_with_passphrase, order_submit, ccxt_okx_mock
):
    mock_exchange, mock_okx_cls = ccxt_okx_mock
    from src.trading.providers import OkxDemoProvider

    provider = OkxDemoProvider()
    receipt = await provider.create_order(creds_with_passphrase, order_submit)

    # 1. CCXT 인스턴스 생성 시 passphrase가 password로 전달됐는지
    mock_okx_cls.assert_called_once()
    cfg = mock_okx_cls.call_args.args[0]
    assert cfg["apiKey"] == "okx-key"
    assert cfg["secret"] == "okx-secret"
    assert cfg["password"] == "okx-pass"
    assert cfg["enableRateLimit"] is True
    assert cfg["timeout"] == 30000
    assert cfg["options"]["defaultType"] == "spot"

    # 2. sandbox mode 활성화 — OKX 고유
    mock_exchange.set_sandbox_mode.assert_called_once_with(True)

    # 3. create_order 인자
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "buy", 0.01, None
    )

    # 4. finally close
    mock_exchange.close.assert_awaited_once()

    # 5. receipt 매핑
    assert receipt.exchange_order_id == "okx-order-7"
    assert receipt.filled_price == Decimal("50421.50")
    assert receipt.status == "filled"


async def test_okx_demo_raises_when_passphrase_missing(order_submit, ccxt_okx_mock):
    from src.trading.exceptions import ProviderError
    from src.trading.providers import Credentials, OkxDemoProvider

    creds = Credentials(api_key="k", api_secret="s", passphrase=None)
    provider = OkxDemoProvider()
    with pytest.raises(ProviderError, match="passphrase"):
        await provider.create_order(creds, order_submit)

    # passphrase 누락은 CCXT 인스턴스 생성 전에 실패해야 함
    _, mock_okx_cls = ccxt_okx_mock
    mock_okx_cls.assert_not_called()


async def test_okx_demo_close_called_on_exchange_error(
    creds_with_passphrase, order_submit, ccxt_okx_mock
):
    mock_exchange, _ = ccxt_okx_mock
    import ccxt.async_support as ccxt_async

    mock_exchange.create_order = AsyncMock(
        side_effect=ccxt_async.InsufficientFunds("balance low")
    )
    from src.trading.exceptions import ProviderError
    from src.trading.providers import OkxDemoProvider

    provider = OkxDemoProvider()
    with pytest.raises(ProviderError, match="InsufficientFunds"):
        await provider.create_order(creds_with_passphrase, order_submit)

    mock_exchange.close.assert_awaited_once()


async def test_okx_demo_non_ccxt_exception_wrapped_safely(
    creds_with_passphrase, order_submit, ccxt_okx_mock
):
    """non-CCXT 예외의 raw traceback에 ccxt.okx instance가 누출되지 않아야 함."""
    mock_exchange, _ = ccxt_okx_mock
    mock_exchange.create_order = AsyncMock(side_effect=KeyError("simulated"))
    from src.trading.exceptions import ProviderError
    from src.trading.providers import OkxDemoProvider

    provider = OkxDemoProvider()
    with pytest.raises(ProviderError, match="unexpected non-CCXT error: KeyError"):
        await provider.create_order(creds_with_passphrase, order_submit)

    mock_exchange.close.assert_awaited_once()


async def test_okx_demo_cancel_order(creds_with_passphrase, ccxt_okx_mock):
    mock_exchange, mock_okx_cls = ccxt_okx_mock
    from src.trading.providers import OkxDemoProvider

    provider = OkxDemoProvider()
    await provider.cancel_order(creds_with_passphrase, "okx-order-7")
    mock_exchange.cancel_order.assert_awaited_once_with("okx-order-7")
    mock_exchange.close.assert_awaited_once()
    # cancel 경로도 sandbox mode 전환
    mock_exchange.set_sandbox_mode.assert_called_once_with(True)
    # cancel 경로의 config에도 password 포함
    cfg = mock_okx_cls.call_args.args[0]
    assert cfg["password"] == "okx-pass"


async def test_okx_demo_cancel_raises_when_passphrase_missing(ccxt_okx_mock):
    from src.trading.exceptions import ProviderError
    from src.trading.providers import Credentials, OkxDemoProvider

    creds = Credentials(api_key="k", api_secret="s", passphrase=None)
    provider = OkxDemoProvider()
    with pytest.raises(ProviderError, match="passphrase"):
        await provider.cancel_order(creds, "x")

    _, mock_okx_cls = ccxt_okx_mock
    mock_okx_cls.assert_not_called()


def test_credentials_repr_masks_passphrase():
    """credentials.__repr__이 passphrase를 평문 노출하지 않는다."""
    from src.trading.providers import Credentials

    c = Credentials(api_key="abcd1234", api_secret="xxx", passphrase="secret-pass")
    rendered = repr(c)
    assert "secret-pass" not in rendered
    assert "passphrase=<present>" in rendered

    c2 = Credentials(api_key="abcd1234", api_secret="xxx", passphrase=None)
    assert "passphrase=<none>" in repr(c2)

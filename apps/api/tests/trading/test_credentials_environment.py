"""Bybit Demo 전용 Credentials 계약 회귀 테스트.

검증:
- exchange/environment 생략 시에도 안전한 Bybit Demo 기본값
- live/OKX 조합은 CCXT client 생성 전 차단
- Bybit Demo만 exchange.enable_demo_trading(True) 호출
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def order_submit_futures():
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit

    return OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.001"),
        price=Decimal("60000"),
        leverage=1,
        margin_mode="cross",
    )


@pytest.fixture
def ccxt_bybit_mock(monkeypatch):
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={
            "id": "bybit-order-42",
            "average": 60000.0,
            "status": "closed",
            "symbol": "BTC/USDT:USDT",
        }
    )
    mock_exchange.cancel_order = AsyncMock(return_value={})
    mock_exchange.set_leverage = AsyncMock(return_value=None)
    mock_exchange.set_margin_mode = AsyncMock(return_value=None)
    mock_exchange.close = AsyncMock()
    # MP-4: precision 변환 stub (str passthrough).
    mock_exchange.load_markets = AsyncMock(return_value={})
    mock_exchange.amount_to_precision = MagicMock(side_effect=lambda symbol, amount: str(amount))
    mock_exchange.price_to_precision = MagicMock(side_effect=lambda symbol, price: str(price))
    mock_exchange.urls = {
        "api": {
            "public": "https://api.bybit.com",
            "private": "https://api.bybit.com",
            "spot": "https://api.bybit.com",
            "futures": "https://api.bybit.com",
            "v2": "https://api.bybit.com",
        }
    }

    mock_bybit_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


# ---------------------------------------------------------------------------
# Credentials 제품 정책
# ---------------------------------------------------------------------------


def test_credentials_default_to_safe_bybit_demo_environment():
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.providers import Credentials

    credentials = Credentials(api_key="k", api_secret="s")

    assert credentials.exchange is ExchangeName.bybit
    assert credentials.environment is ExchangeMode.demo


def test_credentials_live_environment():
    from src.trading.exceptions import BybitDemoOnlyError
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.providers import Credentials

    with pytest.raises(BybitDemoOnlyError):
        Credentials(
            api_key="k",
            api_secret="s",
            exchange=ExchangeName.bybit,
            environment=ExchangeMode.live,
        )


def test_credentials_demo_environment():
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.providers import Credentials

    creds = Credentials(
        api_key="k",
        api_secret="s",
        exchange=ExchangeName.bybit,
        environment=ExchangeMode.demo,
    )
    assert creds.environment == ExchangeMode.demo


def test_credentials_repr_includes_environment():
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.providers import Credentials

    creds = Credentials(
        api_key="abcd1234",
        api_secret="s",
        exchange=ExchangeName.bybit,
        environment=ExchangeMode.demo,
    )
    r = repr(creds)
    assert "environment=demo" in r
    assert "exchange=bybit" in r
    assert "api_secret='***'" in r
    assert "abcd" not in r


# ---------------------------------------------------------------------------
# BybitFuturesProvider — environment 플래그가 CCXT에 전달되는지 검증
# ---------------------------------------------------------------------------


async def test_live_mode_is_blocked_before_creating_a_ccxt_client(
    ccxt_bybit_mock, order_submit_futures
):
    _mock_exchange, mock_bybit_cls = ccxt_bybit_mock
    from src.trading.exceptions import BybitDemoOnlyError
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.providers import Credentials

    with pytest.raises(BybitDemoOnlyError):
        Credentials(
            api_key="key",
            api_secret="secret",
            exchange=ExchangeName.bybit,
            environment=ExchangeMode.live,
        )
    mock_bybit_cls.assert_not_called()


async def test_demo_mode_calls_enable_demo_trading(ccxt_bybit_mock, order_submit_futures):
    """ExchangeMode.demo → testnet=False + enable_demo_trading(True) 호출.

    URL dict 수동 오버라이드 대신 CCXT 공식 API를 사용해야 enableDemoTrading 플래그도
    함께 세팅됨 — 미세팅 시 fetch_balance 내부에서 retCode:10032 발생.
    """
    mock_exchange, mock_bybit_cls = ccxt_bybit_mock
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.providers import BybitFuturesProvider, Credentials

    creds = Credentials(
        api_key="key",
        api_secret="secret",
        exchange=ExchangeName.bybit,
        environment=ExchangeMode.demo,
    )
    provider = BybitFuturesProvider()
    await provider.create_order(creds, order_submit_futures)

    call_kwargs = mock_bybit_cls.call_args[0][0]
    assert call_kwargs["options"]["testnet"] is False
    mock_exchange.enable_demo_trading.assert_called_once_with(True)


# ---------------------------------------------------------------------------
# ExchangeAccountService.get_credentials_for_order — legacy egress 차단
# ---------------------------------------------------------------------------


async def test_get_credentials_live_mode_is_blocked_before_decryption():
    """legacy live account은 평문 자격증명으로 변환되지 않는다."""
    from src.trading.exceptions import BybitDemoOnlyError
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.services.account_service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.live
    account.exchange = ExchangeName.bybit
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = None

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = MagicMock()

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    with pytest.raises(BybitDemoOnlyError):
        await service.get_credentials_for_order(account.id)
    mock_crypto.decrypt.assert_not_called()


async def test_get_credentials_demo_mode_returns_demo_environment():
    """ExchangeMode.demo → environment=demo (api-demo.bybit.com으로 라우팅됨)."""
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.services.account_service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.demo
    account.exchange = ExchangeName.bybit
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = None

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = lambda x: x.decode() if isinstance(x, bytes) else x

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    creds = await service.get_credentials_for_order(account.id)

    assert creds.environment == ExchangeMode.demo
    assert creds.exchange is ExchangeName.bybit


async def test_get_credentials_legacy_okx_is_blocked_before_decryption():
    """삭제하지 않은 OKX 행도 passphrase를 포함해 복호화하지 않는다."""
    from src.trading.exceptions import BybitDemoOnlyError
    from src.trading.models import ExchangeMode, ExchangeName
    from src.trading.services.account_service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.demo
    account.exchange = ExchangeName.okx
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = b"enc_pass"

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = MagicMock()

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    with pytest.raises(BybitDemoOnlyError):
        await service.get_credentials_for_order(account.id)
    mock_crypto.decrypt.assert_not_called()

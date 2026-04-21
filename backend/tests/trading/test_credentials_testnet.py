"""Credentials.testnet 필드 — testnet/live 모드 분기 회귀 테스트.

검증:
- live 모드 계정 → Credentials.testnet=False → CCXT options "testnet": False
- testnet 모드 계정 → Credentials.testnet=True → CCXT options "testnet": True
- default testnet=True (필드 미지정 시 안전 우선)
- tasks/trading.py passphrase 누락 버그 수정 검증 (OKX passphrase 포함)
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

    mock_bybit_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


# ---------------------------------------------------------------------------
# Credentials 기본값
# ---------------------------------------------------------------------------

def test_credentials_default_testnet_is_true():
    from src.trading.providers import Credentials

    creds = Credentials(api_key="k", api_secret="s")
    assert creds.testnet is True


def test_credentials_live_mode():
    from src.trading.providers import Credentials

    creds = Credentials(api_key="k", api_secret="s", testnet=False)
    assert creds.testnet is False


def test_credentials_repr_includes_testnet():
    from src.trading.providers import Credentials

    creds = Credentials(api_key="abcd1234", api_secret="s", testnet=False)
    r = repr(creds)
    assert "testnet=False" in r
    # 민감 필드 마스킹 유지 확인
    assert "api_secret='***'" in r
    assert "abcd" not in r  # api_key 평문 노출 금지


# ---------------------------------------------------------------------------
# BybitFuturesProvider — testnet 플래그가 CCXT에 전달되는지 검증
# ---------------------------------------------------------------------------

async def test_live_mode_sets_testnet_false(
    ccxt_bybit_mock, order_submit_futures
):
    _mock_exchange, mock_bybit_cls = ccxt_bybit_mock
    from src.trading.providers import BybitFuturesProvider, Credentials

    creds = Credentials(api_key="key", api_secret="secret", testnet=False)
    provider = BybitFuturesProvider()
    await provider.create_order(creds, order_submit_futures)

    call_kwargs = mock_bybit_cls.call_args[0][0]
    assert call_kwargs["options"]["testnet"] is False


async def test_testnet_mode_sets_testnet_true(
    ccxt_bybit_mock, order_submit_futures
):
    _mock_exchange, mock_bybit_cls = ccxt_bybit_mock
    from src.trading.providers import BybitFuturesProvider, Credentials

    creds = Credentials(api_key="key", api_secret="secret", testnet=True)
    provider = BybitFuturesProvider()
    await provider.create_order(creds, order_submit_futures)

    call_kwargs = mock_bybit_cls.call_args[0][0]
    assert call_kwargs["options"]["testnet"] is True


# ---------------------------------------------------------------------------
# ExchangeAccountService.get_credentials_for_order — mode → testnet 매핑
# ---------------------------------------------------------------------------

async def test_get_credentials_live_mode_returns_testnet_false():
    """ExchangeMode.live → testnet=False."""
    from unittest.mock import AsyncMock, MagicMock

    from src.trading.models import ExchangeMode
    from src.trading.service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.live
    account.exchange = MagicMock(value="bybit")
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = None

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = lambda x: x.decode() if isinstance(x, bytes) else x

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    creds = await service.get_credentials_for_order(account.id)

    assert creds.testnet is False


async def test_get_credentials_testnet_mode_returns_testnet_true():
    """ExchangeMode.testnet → testnet=True."""
    from unittest.mock import AsyncMock, MagicMock

    from src.trading.models import ExchangeMode
    from src.trading.service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.testnet
    account.exchange = MagicMock(value="bybit")
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = None

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = lambda x: x.decode() if isinstance(x, bytes) else x

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    creds = await service.get_credentials_for_order(account.id)

    assert creds.testnet is True


async def test_get_credentials_demo_mode_returns_testnet_true():
    """ExchangeMode.demo → testnet=True."""
    from unittest.mock import AsyncMock, MagicMock

    from src.trading.models import ExchangeMode
    from src.trading.service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.demo
    account.exchange = MagicMock(value="bybit")
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = None

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = lambda x: x.decode() if isinstance(x, bytes) else x

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    creds = await service.get_credentials_for_order(account.id)

    assert creds.testnet is True


async def test_get_credentials_includes_passphrase():
    """passphrase_encrypted 존재 시 복호화된 값이 Credentials에 포함되는지."""
    from unittest.mock import AsyncMock, MagicMock

    from src.trading.models import ExchangeMode
    from src.trading.service import ExchangeAccountService

    account = MagicMock()
    account.mode = ExchangeMode.testnet
    account.exchange = MagicMock(value="okx")
    account.api_key_encrypted = b"enc_key"
    account.api_secret_encrypted = b"enc_secret"
    account.passphrase_encrypted = b"enc_pass"

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=account)

    mock_crypto = MagicMock()
    mock_crypto.decrypt = lambda x: x.decode() if isinstance(x, bytes) else x

    service = ExchangeAccountService(repo=mock_repo, crypto=mock_crypto)
    creds = await service.get_credentials_for_order(account.id)

    assert creds.passphrase == "enc_pass"
    assert creds.testnet is True

"""Legacy OKX adapter는 어떤 private egress도 시작하지 않는지 검증한다."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.trading.exceptions import BybitDemoOnlyError
from src.trading.models import OrderSide, OrderType
from src.trading.providers import Credentials, OkxDemoProvider, OrderSubmit


@pytest.fixture
def credentials() -> Credentials:
    # passphrase가 있어도 product policy가 먼저 차단해야 한다.
    return Credentials(api_key="okx-key", api_secret="okx-secret", passphrase="okx-pass")


@pytest.fixture
def order_submit() -> OrderSubmit:
    return OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
    )


@pytest.mark.parametrize("operation", ["create", "cancel", "fetch", "fetch_by_client_id"])
async def test_okx_legacy_operations_are_blocked_before_ccxt_client_creation(
    monkeypatch: pytest.MonkeyPatch,
    credentials: Credentials,
    order_submit: OrderSubmit,
    operation: str,
) -> None:
    import ccxt.async_support as ccxt_async

    okx_factory = MagicMock()
    monkeypatch.setattr(ccxt_async, "okx", okx_factory)
    provider = OkxDemoProvider()

    with pytest.raises(BybitDemoOnlyError):
        if operation == "create":
            await provider.create_order(credentials, order_submit)
        elif operation == "cancel":
            await provider.cancel_order(credentials, "okx-order-7", "BTC/USDT")
        elif operation == "fetch":
            await provider.fetch_order(credentials, "okx-order-7", "BTC/USDT")
        else:
            await provider.fetch_order_by_client_id(credentials, "client-7", "BTC/USDT")

    okx_factory.assert_not_called()


def test_credentials_repr_masks_passphrase() -> None:
    credentials = Credentials(api_key="abcd1234", api_secret="xxx", passphrase="secret-pass")

    rendered = repr(credentials)

    assert "secret-pass" not in rendered
    assert "passphrase=<present>" in rendered
    assert "passphrase=<none>" in repr(Credentials(api_key="abcd1234", api_secret="xxx"))

"""FixtureExchangeProvider — 결정적 mock (CCXT 실호출 없음)."""
from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials
    return Credentials(api_key="fake-key", api_secret="fake-secret")


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
    )


async def test_fixture_provider_create_order_returns_deterministic_receipt(credentials, order_submit):
    from src.trading.providers import FixtureExchangeProvider

    provider = FixtureExchangeProvider()
    receipt = await provider.create_order(credentials, order_submit)

    assert receipt.exchange_order_id.startswith("fixture-")
    assert receipt.filled_price == Decimal("50000.00")  # 고정 price
    assert receipt.status == "filled"


async def test_fixture_provider_cancel_order_is_noop(credentials):
    from src.trading.providers import FixtureExchangeProvider

    provider = FixtureExchangeProvider()
    # 예외 없이 리턴
    await provider.cancel_order(credentials, "fixture-xyz")


async def test_fixture_provider_respects_configured_fill_price(credentials, order_submit):
    from src.trading.providers import FixtureExchangeProvider

    provider = FixtureExchangeProvider(fill_price=Decimal("42000.00"))
    receipt = await provider.create_order(credentials, order_submit)
    assert receipt.filled_price == Decimal("42000.00")


async def test_fixture_provider_raises_on_configured_failure(credentials, order_submit):
    """Kill Switch API error streak 테스트용 — 결정적 실패 주입."""
    from src.trading.exceptions import ProviderError
    from src.trading.providers import FixtureExchangeProvider

    provider = FixtureExchangeProvider(fail_next_n=1)
    with pytest.raises(ProviderError):
        await provider.create_order(credentials, order_submit)

    # 그 다음 요청은 정상
    receipt = await provider.create_order(credentials, order_submit)
    assert receipt.status == "filled"


def test_credentials_repr_masks_secrets():
    """SECURITY: Credentials.__repr__ must NOT leak api_key/api_secret plaintext.

    Prevents leaks via tracebacks, structured logs, Sentry, pytest fixture introspection.
    """
    from src.trading.providers import Credentials

    creds = Credentials(api_key="AKIA1234567890SECRET", api_secret="SUPER_SENSITIVE_VALUE")
    rendered = repr(creds)

    assert "SUPER_SENSITIVE_VALUE" not in rendered
    assert "AKIA1234567890SECRET" not in rendered
    assert "CRET" in rendered  # last 4 chars of api_key visible — debug-friendly suffix
    assert "***" in rendered

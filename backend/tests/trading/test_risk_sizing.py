# Wave 2 P2 — 서버 권위 risk-기반 position sizing 가드 검증.
"""max_qty = balance x risk% / |entry-stop|. client qty 초과 시 RiskSizingExceeded.
risk_percent 미설정 / stop·잔고·entry 미가용 시 skip(회귀 0, fail-open)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.exceptions import RiskSizingExceeded
from src.trading.models import OrderSide, OrderType
from src.trading.schemas import OrderRequest


def _make_service(*, balance: Decimal | None, mark: Decimal | None):
    from src.trading.services.order_service import OrderService

    exchange_svc = MagicMock()
    exchange_svc.fetch_balance_usdt = AsyncMock(return_value=balance)
    exchange_svc.fetch_mark_price = AsyncMock(return_value=mark)
    return OrderService(
        session=MagicMock(),
        repo=MagicMock(),
        dispatcher=MagicMock(),
        kill_switch=MagicMock(),
        sessions_port=None,
        exchange_service=exchange_svc,
    )


def _req(**overrides) -> OrderRequest:
    base = {
        "strategy_id": uuid4(),
        "exchange_account_id": uuid4(),
        "symbol": "BTC/USDT",
        "side": OrderSide.buy,
        "type": OrderType.market,
        "quantity": Decimal("0.05"),
        "price": Decimal("50000"),
        "leverage": 5,
        "margin_mode": "cross",
        "stop_loss": Decimal("49000"),
        "risk_percent": Decimal("1"),
    }
    base.update(overrides)
    return OrderRequest(**base)


@pytest.mark.asyncio
async def test_quantity_within_risk_budget_passes() -> None:
    # balance=10000, risk=1% → 100 USDT 손실 허용. stop_distance=1000 → max_qty=0.1.
    # req.quantity=0.05 <= 0.1 → 통과(no raise).
    svc = _make_service(balance=Decimal("10000"), mark=None)
    await svc._validate_position_size(_req(quantity=Decimal("0.05")))


@pytest.mark.asyncio
async def test_quantity_exceeds_risk_budget_rejected() -> None:
    # max_qty=0.1, req.quantity=0.2 → 초과 → RiskSizingExceeded.
    svc = _make_service(balance=Decimal("10000"), mark=None)
    with pytest.raises(RiskSizingExceeded):
        await svc._validate_position_size(_req(quantity=Decimal("0.2")))


@pytest.mark.asyncio
async def test_risk_percent_none_skips() -> None:
    svc = _make_service(balance=Decimal("10000"), mark=None)
    # risk_percent None + qty 과대여도 skip(회귀 0).
    await svc._validate_position_size(_req(quantity=Decimal("5"), risk_percent=None))


@pytest.mark.asyncio
async def test_missing_stop_skips() -> None:
    svc = _make_service(balance=Decimal("10000"), mark=None)
    # stop_loss/trigger_price 둘 다 None → stop 거리 계산 불가 → skip.
    await svc._validate_position_size(
        _req(quantity=Decimal("5"), stop_loss=None, trigger_price=None)
    )


@pytest.mark.asyncio
async def test_zero_balance_skips() -> None:
    svc = _make_service(balance=Decimal("0"), mark=None)
    await svc._validate_position_size(_req(quantity=Decimal("5")))


@pytest.mark.asyncio
async def test_market_order_uses_mark_price_for_entry() -> None:
    # price=None(market) → mark price fetch. mark=50000, stop=49000 → max_qty=0.1.
    svc = _make_service(balance=Decimal("10000"), mark=Decimal("50000"))
    with pytest.raises(RiskSizingExceeded):
        await svc._validate_position_size(
            _req(quantity=Decimal("0.2"), price=None, stop_loss=Decimal("49000"))
        )


@pytest.mark.asyncio
async def test_trigger_price_used_as_stop_when_no_stop_loss() -> None:
    # stop_loss None 이지만 trigger_price=49000 = standalone SL stop → max_qty=0.1.
    svc = _make_service(balance=Decimal("10000"), mark=None)
    with pytest.raises(RiskSizingExceeded):
        await svc._validate_position_size(
            _req(quantity=Decimal("0.2"), stop_loss=None, trigger_price=Decimal("49000"))
        )

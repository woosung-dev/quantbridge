# 포지션 대조 API의 ProviderError HTTP 정규화를 검증한다
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.trading.dependencies import get_close_service, get_position_service
from src.trading.exceptions import ProviderError
from src.trading.models import OrderState
from src.trading.router import router
from src.trading.schemas import (
    AccountPositionRow,
    AccountPositionsResponse,
    ClosePositionResponse,
    ExchangePositionSchema,
)


@pytest.mark.asyncio
async def test_positions_api_maps_provider_error_to_503():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    service = AsyncMock()
    service.get_reconciliation.side_effect = ProviderError("RequestTimeout: unavailable")
    app.dependency_overrides[get_position_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/live-sessions/{uuid4()}/positions")

    assert response.status_code == 503
    assert response.json()["detail"] == "exchange position lookup unavailable"


@pytest.mark.asyncio
async def test_close_positions_api_returns_202() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    service = AsyncMock()
    result = ClosePositionResponse(order_id=uuid4(), state=OrderState.pending, detail="accepted")
    service.close_position.return_value = result
    app.dependency_overrides[get_close_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/live-sessions/{uuid4()}/positions/close")

    assert response.status_code == 202
    assert response.json() == result.model_dump(mode="json")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["fetch", "execute"])
async def test_close_positions_api_maps_provider_error_to_503(source: str) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    service = AsyncMock()
    service.close_position.side_effect = ProviderError(f"{source} unavailable")
    app.dependency_overrides[get_close_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/live-sessions/{uuid4()}/positions/close")

    assert response.status_code == 503
    assert response.json()["detail"] == "exchange position close unavailable"


@pytest.mark.asyncio
async def test_account_positions_api_maps_provider_error_to_503():
    """★BL-498 — 계정 조회 실패도 5xx 로 정규화한다. 빈 목록으로 위장하면 노출을 숨긴다."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    service = AsyncMock()
    service.get_account_positions.side_effect = ProviderError("RequestTimeout: unavailable")
    app.dependency_overrides[get_position_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{uuid4()}/positions")

    assert response.status_code == 503
    assert response.json()["detail"] == "exchange position lookup unavailable"


@pytest.mark.asyncio
async def test_account_positions_api_returns_rows():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    account_id = uuid4()
    session_id = uuid4()
    payload = AccountPositionsResponse(
        account_id=account_id,
        supported=True,
        reason=None,
        fetched_at=datetime(2026, 7, 27, 12, 0, tzinfo=UTC),
        rows=[
            AccountPositionRow(
                symbol="BTC/USDT",
                position=ExchangePositionSchema(
                    side="short",
                    size=Decimal("0.029"),
                    entry_price=Decimal("65340.2"),
                    mark_price=Decimal("65100"),
                    unrealized_pnl=Decimal("7.22"),
                    liquidation_price=None,
                    leverage=Decimal("10"),
                    take_profit_prices=[],
                    stop_loss_prices=[],
                    has_trailing_stop=False,
                ),
                closable_session_id=session_id,
                close_blocked_reason=None,
            )
        ],
        settle_coin="USDT",
        truncated=False,
    )
    service = AsyncMock()
    service.get_account_positions.return_value = payload
    app.dependency_overrides[get_position_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{account_id}/positions")

    assert response.status_code == 200
    body = response.json()
    assert body["rows"][0]["closable_session_id"] == str(session_id)
    assert body["settle_coin"] == "USDT"

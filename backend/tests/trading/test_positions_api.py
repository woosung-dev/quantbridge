# 포지션 대조 API의 ProviderError HTTP 정규화를 검증한다
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.trading.dependencies import get_position_service
from src.trading.exceptions import ProviderError
from src.trading.router import router


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

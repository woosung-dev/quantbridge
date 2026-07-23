# 알림 규칙 CRUD 라우트의 상태 코드와 서비스 위임을 검증한다

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.trading.dependencies import get_alert_rule_service
from src.trading.models import AlertChannel, AlertRuleType
from src.trading.router import router


def _rule(session_id):
    return SimpleNamespace(
        id=uuid4(),
        session_id=session_id,
        rule_type=AlertRuleType.loss_limit,
        threshold_percent=Decimal("5"),
        channel=AlertChannel.slack,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_alert_rules_crud_statuses() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    user = SimpleNamespace(id=uuid4())
    session_id = uuid4()
    rule = _rule(session_id)
    service = SimpleNamespace()
    service.list_active = AsyncMock(return_value=[rule])
    service.create = AsyncMock(return_value=rule)
    service.deactivate = AsyncMock(return_value=None)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_alert_rule_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(f"/api/v1/live-sessions/{session_id}/alert-rules")).status_code == 200
        assert (
            await client.post(
                f"/api/v1/live-sessions/{session_id}/alert-rules",
                json={"rule_type": "loss_limit", "threshold_percent": "5", "channel": "slack"},
            )
        ).status_code == 201
        assert (
            await client.delete(f"/api/v1/live-sessions/{session_id}/alert-rules/{rule.id}")
        ).status_code == 204


@pytest.mark.asyncio
async def test_alert_rules_api_preserves_404_and_409_from_service() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    service = SimpleNamespace()
    service.list_active = AsyncMock(
        side_effect=HTTPException(404, "live session not found")
    )
    service.create = AsyncMock(
        side_effect=HTTPException(409, "active alert rule exists")
    )
    app.dependency_overrides[get_alert_rule_service] = lambda: service
    session_id = uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(f"/api/v1/live-sessions/{session_id}/alert-rules")).status_code == 404
        assert (
            await client.post(
                f"/api/v1/live-sessions/{session_id}/alert-rules",
                json={"rule_type": "watchdog", "channel": "slack"},
            )
        ).status_code == 409

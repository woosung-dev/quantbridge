"""get_current_user dependency — Clerk SDK mock."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_me_without_auth_header_returns_401(client):
    res = await client.get("/api/v1/auth/me")
    # Clerk SDK가 signed_in=False 로 판정 → 401
    assert res.status_code == 401
    body = res.json()
    assert body["detail"]["code"] == "auth_invalid_token"


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client, monkeypatch):
    def _fake_client():
        c = MagicMock()
        req_state = MagicMock()
        req_state.is_signed_in = False
        req_state.reason.name = "token_invalid"
        c.authenticate_request.return_value = req_state
        return c

    monkeypatch.setattr("src.auth.dependencies._clerk_client", _fake_client)

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage"},
    )
    assert res.status_code == 401
    body = res.json()
    assert body["detail"]["code"] == "auth_invalid_token"

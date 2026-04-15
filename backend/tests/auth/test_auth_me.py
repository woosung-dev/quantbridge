"""GET /api/v1/auth/me E2E."""
from __future__ import annotations

import pytest

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser


@pytest.mark.asyncio
async def test_me_returns_current_user(client, app, authed_user):
    async def _fake_current_user() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[get_current_user] = _fake_current_user

    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["clerk_user_id"] == authed_user.clerk_user_id
    assert body["email"] == authed_user.email
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_me_returns_403_when_user_inactive(client, app, authed_user):
    from src.auth.exceptions import UserInactiveError

    async def _fake_current_user() -> CurrentUser:
        raise UserInactiveError()

    app.dependency_overrides[get_current_user] = _fake_current_user

    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "auth_user_inactive"

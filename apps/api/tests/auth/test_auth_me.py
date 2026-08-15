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
    assert body["auth_subject"] == authed_user.auth_subject
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


@pytest.mark.asyncio
async def test_delete_me_requires_authentication(client):
    """음성 대조 — 인증 없이 탈퇴할 수 없다.

    ★이 엔드포인트는 「돈을 멈추는」 경로의 유일한 입구다(ADR-034 · 2026-08-15 surface-truth S3).
    누구나 부를 수 있으면 그 자체가 남의 라이브 세션을 끄는 무기가 된다.
    """
    res = await client.delete("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "auth_invalid_token"


@pytest.mark.asyncio
async def test_delete_me_deactivates_only_the_caller(client, app, authed_user, db_session):
    """양성 — 본인 계정만 잠근다. 204 + `is_active=False`."""
    from src.auth.repository import UserRepository

    async def _fake_current_user() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[get_current_user] = _fake_current_user

    res = await client.delete("/api/v1/auth/me")
    assert res.status_code == 204, res.text

    await db_session.refresh(authed_user)
    reloaded = await UserRepository(db_session).find_by_id(authed_user.id)
    assert reloaded is not None
    assert reloaded.is_active is False

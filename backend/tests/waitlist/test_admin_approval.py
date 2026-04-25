"""Admin approval + listing — 3 TDD.

1. admin approve → invited 상태 + email 발송 (httpx mock)
2. non-admin (일반 사용자) → 403
3. invalid id (존재하지 않음) → 404
"""
from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.waitlist.dependencies import get_email_service, require_admin
from src.waitlist.email_service import EmailService
from src.waitlist.models import WaitlistApplication, WaitlistStatus


def _fast_email_retry() -> None:
    import tenacity

    from src.waitlist import email_service as es_module

    es_module._send_once.retry.wait = tenacity.wait_fixed(0)  # type: ignore[attr-defined]


async def _create_pending_application(
    db_session: AsyncSession,
    *,
    email: str = "pending@example.com",
) -> WaitlistApplication:
    app = WaitlistApplication(
        email=email,
        tv_subscription="pro_plus",
        exchange_capital="1k_to_10k",
        pine_experience="beginner",
        existing_tool=None,
        pain_point="Manual alerts are painful.",
        status=WaitlistStatus.pending,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)
    return app


@pytest.mark.asyncio
async def test_admin_approve_sends_email_and_marks_invited(
    client,
    app: FastAPI,
    authed_user,
    db_session: AsyncSession,
) -> None:
    _fast_email_retry()
    pending = await _create_pending_application(db_session)

    # Admin override — require_admin 을 bypass.
    async def _fake_admin() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[require_admin] = _fake_admin
    app.dependency_overrides[get_current_user] = _fake_admin

    # Email service mock — 실제 외부 호출 차단.
    calls: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        calls.append(_json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"id": "email_mock"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    mock_service = EmailService(api_key="test-key", client=http_client)
    app.dependency_overrides[get_email_service] = lambda: mock_service

    try:
        res = await client.post(f"/api/v1/admin/waitlist/{pending.id}/approve")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "invited"
        assert body["email"] == "pending@example.com"
        assert body["invite_sent_at"] is not None

        # Email 발송 확인
        assert len(calls) == 1
        assert calls[0]["to"] == ["pending@example.com"]
        assert "invited" in calls[0]["subject"].lower()

        # DB state 확인 — endpoint 가 동일 session 을 공유 (dependency override).
        await db_session.refresh(pending)
        assert pending.status == WaitlistStatus.invited
        assert pending.invite_token is not None
        assert pending.invited_at is not None
    finally:
        await http_client.aclose()
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_email_service, None)


@pytest.mark.asyncio
async def test_admin_approve_non_admin_returns_403(
    client,
    app: FastAPI,
    authed_user,
    db_session: AsyncSession,
) -> None:
    """일반 사용자 (authed_user) email 은 WAITLIST_ADMIN_EMAILS 에 없음 → 403."""
    pending = await _create_pending_application(db_session, email="p2@example.com")

    # get_current_user override (일반 사용자). require_admin 은 그대로 동작 → 403.
    async def _fake_current() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[get_current_user] = _fake_current

    try:
        res = await client.post(f"/api/v1/admin/waitlist/{pending.id}/approve")
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "waitlist_admin_only"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_admin_approve_invalid_id_returns_404(
    client,
    app: FastAPI,
    authed_user,
) -> None:
    async def _fake_admin() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[require_admin] = _fake_admin
    app.dependency_overrides[get_current_user] = _fake_admin

    try:
        nonexistent = uuid4()
        res = await client.post(f"/api/v1/admin/waitlist/{nonexistent}/approve")
        assert res.status_code == 404
        assert res.json()["detail"]["code"] == "waitlist_not_found"
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_current_user, None)

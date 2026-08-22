"""Admin approval + listing — 4 TDD.

1. admin approve → invited 상태 + email 발송 (httpx mock)
2. non-admin (일반 사용자) → 403
3. invalid id (존재하지 않음) → 404
4. email 재시도 3회 소진 → 502 **+ DB 는 pending 그대로** (fail-closed)
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


@pytest.mark.asyncio
async def test_admin_approve_retryable_failure_exhausts_retries_and_keeps_pending(
    client,
    app: FastAPI,
    authed_user,
    db_session: AsyncSession,
) -> None:
    """★재시도를 소진한 뒤에도 승인은 **성립하지 않는다** — 502 이고 행은 pending 이다.

    ★이 파일의 다른 케이스·`test_activation_rehearsal.py` 가 이미 덮는 것은 **비재시도**
      분기(401/403 → 즉시 502, 시도 1회)다. 여기가 채우는 공백은 **재시도 분기의 라우터+DB 층**이다 —
      단위 층에는 있었지만(`test_email_service.py::…_500_retry_then_succeeds`,
      `test_waitlist_service_failures.py::test_send_once_uses_retryable_error_for_429`)
      **재시도가 3회 다 실패한 뒤 DB 가 어떻게 되는가**를 엔드포인트로 재는 자리는 없었다.

    ★429 를 고른 이유 — Resend 무료 티어는 100통/일 · 초당 2통 제한이 있어 **연속 승인이
      실제로 만드는 실패**가 이것이다. 401/403(키·도메인)과 달리 429 는 `_is_retryable_status`
      가 True 라 `stop_after_attempt(3)` 을 전부 태우고 `_RetryableError` → `EmailSendError` 다.

    ★★핵심은 시도 횟수가 아니라 **소진 뒤의 DB 상태**다. `admin_approve` 가 메일 → DB 순서라
      (`service.py:112-132`) 3회 실패는 행을 `pending` 에 남긴다 ⇒ 운영자가 `?status=pending`
      목록에서 그 행을 **다시 본다**. 판정 근거는 `docs/operations/waitlist-activation.md` §6.

    ★**판별력의 한계를 정직하게 적는다** — 2026-08-23 변이 2종(`_is_retryable_status` → `False`,
      `stop_after_attempt(3)` → `2`)이 이 테스트를 red 로 만들지만 **둘 다 격리되지 않았다**
      (기존 단위 테스트 2~3건이 같이 red). 즉 **이 테스트만 잡는 변이는 찾지 못했다.**
      그럼에도 남기는 근거는 커버리지가 아니라 **조합**이다 — 재시도 대상 실패를 `POST …/approve`
      로 통과시키는 케이스가 이 파일 이전에 **0건**이었다(기존 endpoint 케이스는 전부 401/403
      비재시도). 단위가 옳다는 것과 그 배선이 옳다는 것은 다르다([LESSON-092] 2번).
    """
    _fast_email_retry()
    pending = await _create_pending_application(db_session, email="failsend@example.com")

    async def _fake_admin() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[require_admin] = _fake_admin
    app.dependency_overrides[get_current_user] = _fake_admin

    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(429, json={"message": "Too many requests"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    app.dependency_overrides[get_email_service] = lambda: EmailService(
        api_key="test-key", client=http_client
    )

    try:
        res = await client.post(f"/api/v1/admin/waitlist/{pending.id}/approve")
        assert res.status_code == 502, res.text
        assert res.json()["detail"]["code"] == "waitlist_email_send_failed"

        # 429 는 재시도 대상 — `stop_after_attempt(3)` 을 전부 태운다.
        # 1 이 나오면 재시도가 죽은 것이고, 4 이상이면 상한이 풀린 것이다.
        assert len(attempts) == 3, attempts

        # ★핵심 — 재시도를 다 쓰고도 DB 는 전환되지 않았다. 재승인이 안전하다.
        await db_session.refresh(pending)
        assert pending.status == WaitlistStatus.pending
        assert pending.invite_token is None
        assert pending.invited_at is None
        assert pending.invite_sent_at is None
    finally:
        await http_client.aclose()
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_email_service, None)

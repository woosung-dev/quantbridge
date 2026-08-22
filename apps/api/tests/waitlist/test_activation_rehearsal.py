"""[beta-unlock] Waitlist 활성화 **종단 리허설** — 등록 → 승인 → 메일 → /invite 검증 1회 통과.

★기존 8파일이 이미 각 홉을 낱개로 재고 있다(46 passed). 여기가 채우는 공백은 **사슬**이다 —
  종전에는 `POST /waitlist` 로 만들어진 행이 `approve` 를 거쳐 **메일 본문에 실린 그 토큰**으로
  `/waitlist/invite/{token}` 을 통과하는지 재는 자리가 없었다. `test_admin_approval.py` 는
  DB 에 직접 심은 행에서 출발하고 토큰을 **DB 에서** 꺼낸다 — 즉 「메일에 실린 링크가 실제로
  열리는가」는 아무도 재지 않았다. 이 파일이 `docs/operations/waitlist-activation.md` 의
  「판정 기준」 4단계와 1:1 대응하는 실행 가능한 증거다.

★**스텁은 Resend HTTP 하나뿐이다.** 라우터·서비스·리포지터리·토큰 서비스·DB·`require_admin`
  화이트리스트는 전부 실경로다. `EmailService` 도 실물이고 **transport 만** 가짜다 —
  페이로드 렌더링·상태코드 판정·retry 분기가 그대로 돈다.
"""

from __future__ import annotations

import json as _json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.waitlist.dependencies import get_email_service
from src.waitlist.email_service import EmailService
from src.waitlist.models import WaitlistApplication, WaitlistStatus

# 리허설 전용 고정값 — 판정이 .env.local 값에 흔들리지 않게 못박는다.
REHEARSAL_INVITE_BASE = "https://qb.example.test/invite"
REHEARSAL_FROM = "QuantBridge <noreply@qb.example.test>"
REHEARSAL_API_KEY = "re_rehearsal_key_not_a_real_secret"

APPLICANT = {
    "email": "Rehearsal.Applicant@Example.com",  # 대소문자 정규화도 사슬에서 함께 잰다
    "tv_subscription": "pro_plus",
    "exchange_capital": "1k_to_10k",
    "pine_experience": "intermediate",
    "existing_tool": None,
    "pain_point": "TradingView 알림을 손으로 옮겨 담다가 체결을 놓칩니다.",
}


class _ResendStub:
    """Resend 의 HTTP 표면만 대신한다 — 요청을 통째로 보관해 사후 단언에 쓴다."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.requests: list[httpx.Request] = []
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.payloads.append(_json.loads(request.content.decode("utf-8")))
        if self.status_code >= 400:
            return httpx.Response(self.status_code, json={"message": "stubbed failure"})
        return httpx.Response(200, json={"id": "email_rehearsal"})


def _install_resend_stub(app: FastAPI, stub: _ResendStub) -> httpx.AsyncClient:
    """`get_email_service` 만 갈아끼운다 — 서비스는 실물, transport 만 가짜다."""
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(stub))
    app.dependency_overrides[get_email_service] = lambda: EmailService(
        api_key=REHEARSAL_API_KEY,
        from_address=REHEARSAL_FROM,
        client=http_client,
    )
    return http_client


@pytest.fixture
def _rehearsal_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.core.config.settings.waitlist_invite_base_url", REHEARSAL_INVITE_BASE)
    monkeypatch.setattr("src.core.config.settings.resend_from_address", REHEARSAL_FROM)


async def _fetch_application(session: AsyncSession, email: str) -> WaitlistApplication:
    result = await session.execute(
        select(WaitlistApplication).where(
            WaitlistApplication.email == email  # type: ignore[arg-type]
        )
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_activation_rehearsal_signup_to_invite_verify(
    client,
    app: FastAPI,
    mock_authed_user,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    _rehearsal_settings: None,
) -> None:
    """런북 §판정 기준 ①~④ — 네 관측점을 한 사슬로 통과시킨다."""
    # 관리자 화이트리스트를 **실경로로** 켠다 — `require_admin` 을 override 하지 않는다.
    monkeypatch.setattr(
        "src.core.config.settings.waitlist_admin_emails_raw", mock_authed_user.email
    )
    stub = _ResendStub()
    http_client = _install_resend_stub(app, stub)

    try:
        # ① 대기자 등록 — 공개 엔드포인트, 인증 없음.
        res = await client.post("/api/v1/waitlist", json=APPLICANT)
        assert res.status_code == 202, res.text
        application_id = res.json()["id"]
        assert res.json()["status"] == "pending"

        stored = await _fetch_application(db_session, "rehearsal.applicant@example.com")
        assert stored.status == WaitlistStatus.pending
        assert stored.invite_token is None

        # ② 관리자 목록 — 화이트리스트 통과가 여기서 처음 증명된다.
        listed = await client.get("/api/v1/admin/waitlist", params={"status": "pending"})
        assert listed.status_code == 200, listed.text
        assert any(item["id"] == application_id for item in listed.json()["items"])

        # ③ 승인 — 메일 발송 후 DB 전환.
        approved = await client.post(f"/api/v1/admin/waitlist/{application_id}/approve")
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "invited"
        assert approved.json()["invite_sent_at"] is not None

        # Resend 로 나간 요청이 정확히 1건이고, 키·발신자·수신자가 설정에서 왔다.
        assert len(stub.requests) == 1
        assert stub.requests[0].headers["Authorization"] == f"Bearer {REHEARSAL_API_KEY}"
        payload = stub.payloads[0]
        assert payload["from"] == REHEARSAL_FROM
        assert payload["to"] == ["rehearsal.applicant@example.com"]

        # ④ **메일 본문에 실린 링크**에서 토큰을 꺼낸다 — DB 에서 꺼내면 이 사슬이 무의미하다.
        prefix = f"{REHEARSAL_INVITE_BASE}/"
        assert prefix in payload["text"], payload["text"]
        token = payload["text"].split(prefix, 1)[1].split()[0].strip()
        assert token, "메일 본문에서 토큰을 못 꺼냈다"
        assert f'href="{prefix}{token}"' in payload["html"]

        verified = await client.get(f"/api/v1/waitlist/invite/{token}")
        assert verified.status_code == 200, verified.text
        assert verified.json() == {
            "email": "rehearsal.applicant@example.com",
            "status": "invited",
        }

        await db_session.refresh(stored)
        assert stored.status == WaitlistStatus.invited
        assert stored.invite_token == token
    finally:
        await http_client.aclose()
        app.dependency_overrides.pop(get_email_service, None)


@pytest.mark.asyncio
async def test_activation_fail_closed_admin_emails_unset(
    client,
    app: FastAPI,
    mock_authed_user,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    _rehearsal_settings: None,
) -> None:
    """★fail-closed ① — `WAITLIST_ADMIN_EMAILS` 미설정이면 승인이 403 이고 메일은 0건이다.

    `require_admin` 은 빈 화이트리스트를 「전원 허용」이 아니라 **전원 거부**로 읽는다
    (`dependencies.py:67` — `if not allowed or ...`). 이 단언이 그 방향을 고정한다.
    """
    monkeypatch.setattr("src.core.config.settings.waitlist_admin_emails_raw", "")
    stub = _ResendStub()
    http_client = _install_resend_stub(app, stub)

    try:
        res = await client.post("/api/v1/waitlist", json=APPLICANT)
        assert res.status_code == 202, res.text
        application_id = res.json()["id"]

        denied = await client.post(f"/api/v1/admin/waitlist/{application_id}/approve")
        assert denied.status_code == 403
        assert denied.json()["detail"]["code"] == "waitlist_admin_only"

        # 메일은 나가지 않았고 행은 그대로 pending 이다.
        assert stub.requests == []
        stored = await _fetch_application(db_session, "rehearsal.applicant@example.com")
        assert stored.status == WaitlistStatus.pending
        assert stored.invite_token is None
    finally:
        await http_client.aclose()
        app.dependency_overrides.pop(get_email_service, None)


@pytest.mark.asyncio
async def test_activation_fail_closed_resend_rejects_key(
    client,
    app: FastAPI,
    mock_authed_user,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    _rehearsal_settings: None,
) -> None:
    """★fail-closed ② — Resend 가 키를 거부(401)하면 502 이고 **DB 는 pending 에 머문다**.

    `RESEND_API_KEY` 미설정의 실제 증상이 이것이다 — `get_email_service` 가
    `api_key or "dev-empty-key"` 로 **부팅은 통과**시키므로(`dependencies.py:40`)
    결함은 부팅이 아니라 **승인 요청 시점**에 드러난다.
    401 은 재시도 대상이 아니므로(`_is_retryable_status`) 시도는 1회다.

    ★이 순서(메일 → DB)가 의도인지 결함인지의 판정은 런북 §6 에 적었다 — **의도이고 옳다**.
      뒤집으면 발송 실패가 「받은 사람이 없는 invited」를 만들어 재시도 신호가 사라진다.
    """
    monkeypatch.setattr(
        "src.core.config.settings.waitlist_admin_emails_raw", mock_authed_user.email
    )
    stub = _ResendStub(status_code=401)
    http_client = _install_resend_stub(app, stub)

    try:
        res = await client.post("/api/v1/waitlist", json=APPLICANT)
        assert res.status_code == 202, res.text
        application_id = res.json()["id"]

        failed = await client.post(f"/api/v1/admin/waitlist/{application_id}/approve")
        assert failed.status_code == 502
        assert failed.json()["detail"]["code"] == "waitlist_email_send_failed"

        # 401 은 재시도하지 않는다 — 정확히 1회.
        assert len(stub.requests) == 1

        # ★핵심 단언 — 전이가 막혔다. 운영자는 pending 목록에서 이 행을 다시 본다.
        stored = await _fetch_application(db_session, "rehearsal.applicant@example.com")
        assert stored.status == WaitlistStatus.pending
        assert stored.invite_token is None
        assert stored.invite_sent_at is None
    finally:
        await http_client.aclose()
        app.dependency_overrides.pop(get_email_service, None)

"""`/api/v1/push/*` HTTP 계약 (pwa.md §3.2 · §3.6)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.notifications.dependencies import get_push_sender
from src.notifications.dispatcher import TEST_PUSH_PAYLOAD
from src.notifications.models import PushSubscription
from tests.notifications.helpers import (
    ENDPOINT_A,
    ENDPOINT_B,
    ENDPOINT_C,
    VAPID,
    FakeSender,
    seed_subscription,
    subscribe_body,
)

_BASE = "/api/v1/push"


async def _other_user(session: AsyncSession) -> User:
    user = User(auth_subject=f"other_{uuid4().hex[:8]}", email=f"o_{uuid4().hex[:6]}@ex.com")
    session.add(user)
    await session.flush()
    return user


async def _rows(session: AsyncSession, endpoint: str) -> list[PushSubscription]:
    result = await session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)  # type: ignore[arg-type]
    )
    return list(result.scalars().all())


# --- config -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_config_disabled_when_vapid_unset(
    client: AsyncClient, mock_authed_user: User, vapid_off: None
) -> None:
    res = await client.get(f"{_BASE}/config")

    assert res.status_code == 200
    assert res.json() == {"enabled": False, "public_key": None}


@pytest.mark.asyncio
async def test_get_config_returns_public_key_when_configured(
    client: AsyncClient, mock_authed_user: User, vapid_on: None
) -> None:
    res = await client.get(f"{_BASE}/config")

    assert res.status_code == 200
    assert res.json() == {"enabled": True, "public_key": VAPID.public_key}


@pytest.mark.asyncio
async def test_get_config_disabled_when_any_one_vapid_key_missing(
    client: AsyncClient, mock_authed_user: User, vapid_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """「3종 중 하나라도」 — 둘만 있어도 꺼진다(subject 만 비운다)."""
    monkeypatch.setattr("src.core.config.settings.vapid_subject", None)

    res = await client.get(f"{_BASE}/config")

    assert res.json() == {"enabled": False, "public_key": None}


@pytest.mark.asyncio
async def test_endpoints_require_auth(client: AsyncClient) -> None:
    """4개 엔드포인트 전부 Bearer 없이 401 — `get_current_user` 를 override 하지 않는다."""
    responses = [
        await client.get(f"{_BASE}/config"),
        await client.post(f"{_BASE}/subscriptions", json=subscribe_body(ENDPOINT_A)),
        await client.request("DELETE", f"{_BASE}/subscriptions", json={"endpoint": ENDPOINT_A}),
        await client.post(f"{_BASE}/test"),
    ]

    assert [r.status_code for r in responses] == [401, 401, 401, 401]


# --- subscribe --------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_creates_row(
    client: AsyncClient, mock_authed_user: User, db_session: AsyncSession
) -> None:
    res = await client.post(f"{_BASE}/subscriptions", json=subscribe_body(ENDPOINT_A))

    assert res.status_code == 201
    body = res.json()
    assert body["endpoint"] == ENDPOINT_A
    assert set(body) == {"id", "endpoint", "created_at"}
    rows = await _rows(db_session, ENDPOINT_A)
    assert len(rows) == 1
    assert rows[0].user_id == mock_authed_user.id
    assert (rows[0].p256dh, rows[0].auth, rows[0].user_agent) == ("p256dh-a", "auth-a", "pytest-ua")


@pytest.mark.asyncio
async def test_subscribe_same_endpoint_is_upsert(
    client: AsyncClient, mock_authed_user: User, db_session: AsyncSession
) -> None:
    first = await client.post(f"{_BASE}/subscriptions", json=subscribe_body(ENDPOINT_A))
    second_body = subscribe_body(ENDPOINT_A, user_agent="new-ua")
    second_body["keys"] = {"p256dh": "rotated-p256dh", "auth": "rotated-auth"}
    second = await client.post(f"{_BASE}/subscriptions", json=second_body)

    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    count = (
        await db_session.execute(select(func.count()).select_from(PushSubscription))
    ).scalar_one()
    assert count == 1
    row = (await _rows(db_session, ENDPOINT_A))[0]
    assert (row.p256dh, row.auth, row.user_agent) == ("rotated-p256dh", "rotated-auth", "new-ua")


@pytest.mark.asyncio
async def test_subscribe_endpoint_reassigned_to_current_user(
    client: AsyncClient, mock_authed_user: User, db_session: AsyncSession
) -> None:
    """공용 기기 — 이전 사용자의 같은 endpoint 행이 현재 사용자로 **이동**한다(새 행 아님)."""
    other = await _other_user(db_session)
    seeded = await seed_subscription(db_session, other.id, ENDPOINT_A)
    await db_session.commit()

    res = await client.post(f"{_BASE}/subscriptions", json=subscribe_body(ENDPOINT_A))

    assert res.status_code == 200
    rows = await _rows(db_session, ENDPOINT_A)
    assert len(rows) == 1
    assert rows[0].id == seeded.id
    assert rows[0].user_id == mock_authed_user.id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [
        "https://fcm.googleapis.com/fcm/send/abc",
        "https://updates.push.services.mozilla.com/wpush/v2/abc",
        "https://web.push.apple.com/QGx",
        "https://wns2-par02p.notify.windows.com/w/?token=abc",
    ],
)
async def test_subscribe_accepts_known_push_service_hosts(
    client: AsyncClient, mock_authed_user: User, endpoint: str
) -> None:
    res = await client.post(f"{_BASE}/subscriptions", json=subscribe_body(endpoint))

    assert res.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [
        "http://169.254.169.254/latest",  # 평문 + 메타데이터 주소
        "https://internal.example.com/push",  # 임의 https 호스트
        "https://redis/push",  # compose 내부 서비스명
        "https://fcm.googleapis.com.evil.com/fcm/send/abc",  # 접두 위장
        "https://fcm.googleapis.com@evil.com/fcm/send/abc",  # userinfo 위장
        "https://evilnotify.windows.com/w",  # 점 없는 접미 위장
        "https://push.apple.com.attacker.net/x",  # 접미 뒤 덧붙이기
        "https://fcm.googleapis.com:6379/fcm/send/abc",  # 비표준 포트
    ],
)
async def test_subscribe_rejects_non_push_service_endpoint(
    client: AsyncClient, mock_authed_user: User, db_session: AsyncSession, endpoint: str
) -> None:
    """[SSRF] 서버가 POST 할 대상이므로 알려진 푸시 서비스 호스트 밖은 422, 행도 안 생긴다."""
    res = await client.post(f"{_BASE}/subscriptions", json=subscribe_body(endpoint))

    assert res.status_code == 422
    assert await _rows(db_session, endpoint) == []


# --- unsubscribe ------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_own_endpoint_204(
    client: AsyncClient, mock_authed_user: User, db_session: AsyncSession
) -> None:
    await seed_subscription(db_session, mock_authed_user.id, ENDPOINT_A)
    await db_session.commit()

    res = await client.request("DELETE", f"{_BASE}/subscriptions", json={"endpoint": ENDPOINT_A})

    assert res.status_code == 204
    assert res.content == b""
    assert await _rows(db_session, ENDPOINT_A) == []


@pytest.mark.asyncio
async def test_unsubscribe_other_users_endpoint_404(
    client: AsyncClient, mock_authed_user: User, db_session: AsyncSession
) -> None:
    """남의 endpoint 와 없는 endpoint 가 **같은 404** — 존재 여부를 흘리지 않는다."""
    other = await _other_user(db_session)
    await seed_subscription(db_session, other.id, ENDPOINT_A)
    await db_session.commit()

    others = await client.request("DELETE", f"{_BASE}/subscriptions", json={"endpoint": ENDPOINT_A})
    missing = await client.request(
        "DELETE", f"{_BASE}/subscriptions", json={"endpoint": ENDPOINT_B}
    )

    assert (others.status_code, missing.status_code) == (404, 404)
    assert others.json() == missing.json()
    assert len(await _rows(db_session, ENDPOINT_A)) == 1


# --- test push --------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_test_endpoint_reports_sent_and_removed(
    app: FastAPI,
    client: AsyncClient,
    mock_authed_user: User,
    db_session: AsyncSession,
    vapid_on: None,
) -> None:
    """내 구독 3개(성공 · 410 · 500) → `{sent: 1, removed: 1}`. 남의 구독에는 안 보낸다."""
    await seed_subscription(db_session, mock_authed_user.id, ENDPOINT_A)
    await seed_subscription(db_session, mock_authed_user.id, ENDPOINT_B)
    await seed_subscription(db_session, mock_authed_user.id, ENDPOINT_C)
    other = await _other_user(db_session)
    await seed_subscription(db_session, other.id, "https://fcm.googleapis.com/fcm/send/other")
    await db_session.commit()
    sender = FakeSender({ENDPOINT_A: 201, ENDPOINT_B: 410, ENDPOINT_C: 500})
    app.dependency_overrides[get_push_sender] = lambda: sender

    res = await client.post(f"{_BASE}/test")

    assert res.status_code == 200
    assert res.json() == {"sent": 1, "removed": 1}
    assert sorted(endpoint for endpoint, _ in sender.calls) == sorted(
        [ENDPOINT_A, ENDPOINT_B, ENDPOINT_C]
    )
    assert all(payload == TEST_PUSH_PAYLOAD for _, payload in sender.calls)
    assert (await _rows(db_session, ENDPOINT_A))[0].last_success_at is not None
    assert await _rows(db_session, ENDPOINT_B) == []
    assert (await _rows(db_session, ENDPOINT_C))[0].last_success_at is None


@pytest.mark.asyncio
async def test_push_test_endpoint_409_when_disabled(
    app: FastAPI, client: AsyncClient, mock_authed_user: User, vapid_off: None
) -> None:
    sender = FakeSender({})
    app.dependency_overrides[get_push_sender] = lambda: sender

    res = await client.post(f"{_BASE}/test")

    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "push_disabled"
    assert sender.calls == []

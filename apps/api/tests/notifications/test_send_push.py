"""발송 — 404·410 삭제 / 그 외 유지 / VAPID 없으면 0 (pwa.md §3.4 · §3.6)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.notifications.repository import PushSubscriptionRepository
from src.notifications.service import PushNotificationService, PushSendResult
from src.notifications.webpush_client import VapidConfig
from src.tasks import notifications as push_task
from tests.notifications.helpers import ENDPOINT_A, ENDPOINT_B, VAPID, FakeSender, seed_subscription

_PAYLOAD = {"title": "주문 체결", "body": "BTC/USDT:USDT buy", "url": "/trading", "tag": "order:1"}


def _service(
    session: AsyncSession, sender: FakeSender, vapid: VapidConfig | None = VAPID
) -> PushNotificationService:
    return PushNotificationService(
        repo=PushSubscriptionRepository(session), vapid=vapid, sender=sender
    )


@pytest.mark.asyncio
async def test_send_push_deletes_subscription_on_410(
    db_session: AsyncSession, authed_user: User
) -> None:
    await seed_subscription(db_session, authed_user.id, ENDPOINT_A)
    sender = FakeSender({ENDPOINT_A: 410})

    result = await _service(db_session, sender).send_push(authed_user.id, _PAYLOAD)

    assert result == PushSendResult(sent=0, removed=1)
    assert sender.calls == [(ENDPOINT_A, _PAYLOAD)]
    assert await PushSubscriptionRepository(db_session).find_by_endpoint(ENDPOINT_A) is None


@pytest.mark.asyncio
async def test_send_push_deletes_subscription_on_404(
    db_session: AsyncSession, authed_user: User
) -> None:
    await seed_subscription(db_session, authed_user.id, ENDPOINT_A)
    sender = FakeSender({ENDPOINT_A: 404})

    result = await _service(db_session, sender).send_push(authed_user.id, _PAYLOAD)

    assert result == PushSendResult(sent=0, removed=1)
    assert await PushSubscriptionRepository(db_session).find_by_endpoint(ENDPOINT_A) is None


@pytest.mark.asyncio
async def test_send_push_keeps_subscription_on_500(
    db_session: AsyncSession, authed_user: User
) -> None:
    """5xx 응답과 네트워크 예외 둘 다 「그 외 실패」 — 로그만, 행은 남고 재시도도 없다."""
    await seed_subscription(db_session, authed_user.id, ENDPOINT_A)
    await seed_subscription(db_session, authed_user.id, ENDPOINT_B)
    sender = FakeSender({ENDPOINT_A: 500, ENDPOINT_B: ConnectionError("push service down")})

    result = await _service(db_session, sender).send_push(authed_user.id, _PAYLOAD)

    assert result == PushSendResult(sent=0, removed=0)
    assert len(sender.calls) == 2
    repo = PushSubscriptionRepository(db_session)
    for endpoint in (ENDPOINT_A, ENDPOINT_B):
        row = await repo.find_by_endpoint(endpoint)
        assert row is not None
        assert row.last_success_at is None


@pytest.mark.asyncio
async def test_send_push_noop_when_vapid_unset(
    db_session: AsyncSession,
    authed_user: User,
    vapid_off: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """서비스는 발신기를 부르지 않고, Celery 진입점은 DB 조차 열지 않는다."""
    await seed_subscription(db_session, authed_user.id, ENDPOINT_A)
    sender = FakeSender({ENDPOINT_A: 201})

    result = await _service(db_session, sender, vapid=None).send_push(authed_user.id, _PAYLOAD)

    assert result == PushSendResult(sent=0, removed=0)
    assert sender.calls == []

    def _must_not_open_db() -> object:
        raise AssertionError("VAPID 가 없는데 worker engine 을 만들었다")

    monkeypatch.setattr(push_task, "create_worker_engine_and_sm", _must_not_open_db)

    assert await push_task.send_push(uuid4(), _PAYLOAD) == {"sent": 0, "removed": 0}

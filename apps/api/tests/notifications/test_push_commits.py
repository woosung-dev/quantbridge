"""[LESSON-019] notifications service mutation commit-spy.

`get_async_session()` 은 autocommit OFF 라 commit 이 없으면 요청 끝에 ROLLBACK 이다.
`db_session` 통합 테스트는 같은 트랜잭션 안 read-your-writes 로 **그래도 통과**하므로
mutation 메서드마다 repo.commit 을 직접 잰다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.notifications.exceptions import PushSubscriptionNotFoundError
from src.notifications.models import PushSubscription
from src.notifications.schemas import CreatePushSubscriptionRequest
from src.notifications.service import PushNotificationService
from tests.notifications.helpers import ENDPOINT_A, VAPID, FakeSender, subscribe_body


def _row(user_id: object) -> PushSubscription:
    return PushSubscription(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        endpoint=ENDPOINT_A,
        p256dh="p",
        auth="a",
        created_at=datetime.now(UTC),
    )


def _service(repo: AsyncMock, sender: FakeSender | None = None) -> PushNotificationService:
    return PushNotificationService(repo=repo, vapid=VAPID, sender=sender or FakeSender({}))


@pytest.mark.asyncio
async def test_subscribe_new_calls_repo_commit() -> None:
    user_id = uuid4()
    repo = AsyncMock()
    repo.find_by_endpoint.return_value = None
    repo.create.return_value = _row(user_id)

    _, created = await _service(repo).subscribe(
        user_id, CreatePushSubscriptionRequest.model_validate(subscribe_body(ENDPOINT_A))
    )

    assert created is True
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscribe_existing_calls_repo_commit() -> None:
    user_id = uuid4()
    existing = _row(uuid4())
    repo = AsyncMock()
    repo.find_by_endpoint.return_value = existing
    repo.reassign.return_value = _row(user_id)

    _, created = await _service(repo).subscribe(
        user_id, CreatePushSubscriptionRequest.model_validate(subscribe_body(ENDPOINT_A))
    )

    assert created is False
    repo.reassign.assert_awaited_once()
    assert repo.reassign.await_args.kwargs["user_id"] == user_id
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsubscribe_calls_repo_commit() -> None:
    user_id = uuid4()
    repo = AsyncMock()
    repo.find_by_endpoint.return_value = _row(user_id)

    await _service(repo).unsubscribe(user_id, ENDPOINT_A)

    repo.delete.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsubscribe_other_users_endpoint_does_not_commit() -> None:
    repo = AsyncMock()
    repo.find_by_endpoint.return_value = _row(uuid4())

    with pytest.raises(PushSubscriptionNotFoundError):
        await _service(repo).unsubscribe(uuid4(), ENDPOINT_A)

    repo.delete.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_send_push_calls_repo_commit() -> None:
    user_id = uuid4()
    repo = AsyncMock()
    repo.list_by_user.return_value = [_row(user_id)]

    await _service(repo, FakeSender({ENDPOINT_A: 410})).send_push(user_id, {"title": "t"})

    repo.delete.assert_awaited_once()
    repo.commit.assert_awaited_once()

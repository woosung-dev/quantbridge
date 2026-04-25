"""UserService 단위 테스트 (repository mock)."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.auth.models import User
from src.auth.service import UserService


@pytest.fixture
def user_repo_mock():
    repo = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def strategy_repo_mock():
    return AsyncMock()


@pytest.fixture
def service(user_repo_mock, strategy_repo_mock):
    return UserService(user_repo=user_repo_mock, strategy_repo=strategy_repo_mock)


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_when_found(service, user_repo_mock):
    existing = User(id=uuid4(), clerk_user_id="user_x", email="a@b.com", username="a")
    user_repo_mock.find_by_clerk_id.return_value = existing

    result = await service.get_or_create("user_x", email="a@b.com", username="a")

    assert result is existing
    user_repo_mock.insert_if_absent.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_updates_profile_on_change(service, user_repo_mock):
    existing = User(id=uuid4(), clerk_user_id="user_x", email="old@b.com", username="old")
    updated = User(id=existing.id, clerk_user_id="user_x", email="new@b.com", username="new")
    user_repo_mock.find_by_clerk_id.return_value = existing
    user_repo_mock.update_profile.return_value = updated

    result = await service.get_or_create("user_x", email="new@b.com", username="new")

    user_repo_mock.update_profile.assert_awaited_once()
    assert result.email == "new@b.com"


@pytest.mark.asyncio
async def test_get_or_create_inserts_when_missing(service, user_repo_mock):
    created = User(id=uuid4(), clerk_user_id="user_y", email="y@b.com", username="y")
    user_repo_mock.find_by_clerk_id.return_value = None
    user_repo_mock.insert_if_absent.return_value = created

    result = await service.get_or_create("user_y", email="y@b.com", username="y")

    user_repo_mock.insert_if_absent.assert_awaited_once()
    assert result is created


@pytest.mark.asyncio
async def test_handle_user_created_event_upserts(service, user_repo_mock):
    event = {
        "type": "user.created",
        "data": {
            "id": "user_z",
            "email_addresses": [{"id": "e1", "email_address": "z@b.com"}],
            "primary_email_address_id": "e1",
            "username": "z",
        },
    }
    await service.handle_clerk_event(event)

    # Sprint 11 Phase A — country_code 는 public_metadata 없으면 None.
    user_repo_mock.upsert_from_webhook.assert_awaited_once_with(
        clerk_user_id="user_z", email="z@b.com", username="z", country_code=None
    )


@pytest.mark.asyncio
async def test_handle_user_deleted_archives_strategies(service, user_repo_mock, strategy_repo_mock):
    existing = User(id=uuid4(), clerk_user_id="user_gone", email=None, username=None, is_active=True)
    user_repo_mock.find_by_clerk_id.return_value = existing

    event = {"type": "user.deleted", "data": {"id": "user_gone"}}
    await service.handle_clerk_event(event)

    user_repo_mock.set_inactive.assert_awaited_once_with(existing.id)
    strategy_repo_mock.archive_all_by_owner.assert_awaited_once_with(existing.id)


@pytest.mark.asyncio
async def test_handle_unknown_event_is_noop(service, user_repo_mock, strategy_repo_mock):
    await service.handle_clerk_event({"type": "session.created", "data": {}})

    user_repo_mock.upsert_from_webhook.assert_not_awaited()
    user_repo_mock.set_inactive.assert_not_awaited()

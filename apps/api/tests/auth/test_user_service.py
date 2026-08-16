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
    existing = User(id=uuid4(), auth_subject="user_x", email="a@b.com", username="a")
    user_repo_mock.find_by_auth_subject.return_value = existing

    result = await service.get_or_create("user_x", email="a@b.com", username="a")

    assert result is existing
    user_repo_mock.insert_if_absent.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_updates_profile_on_change(service, user_repo_mock):
    existing = User(id=uuid4(), auth_subject="user_x", email="old@b.com", username="old")
    updated = User(id=existing.id, auth_subject="user_x", email="new@b.com", username="new")
    user_repo_mock.find_by_auth_subject.return_value = existing
    user_repo_mock.update_profile.return_value = updated

    result = await service.get_or_create("user_x", email="new@b.com", username="new")

    user_repo_mock.update_profile.assert_awaited_once()
    assert result.email == "new@b.com"


@pytest.mark.asyncio
async def test_get_or_create_inserts_when_missing(service, user_repo_mock):
    created = User(id=uuid4(), auth_subject="user_y", email="y@b.com", username="y")
    user_repo_mock.find_by_auth_subject.return_value = None
    user_repo_mock.insert_if_absent.return_value = created

    result = await service.get_or_create("user_y", email="y@b.com", username="y")

    user_repo_mock.insert_if_absent.assert_awaited_once()
    assert result is created


@pytest.mark.asyncio
async def test_deactivate_account_archives_strategies(service, user_repo_mock, strategy_repo_mock):
    """탈퇴 — 계정 잠금 + 전략 archive 가 같은 트랜잭션에서 일어난다.

    ★입구가 Clerk `user.deleted` 웹훅에서 `DELETE /auth/me` 로 바뀌었을 뿐, **안에서 하는 일은
    같아야 한다**(ADR-034). 얇아지면 2026-08-15 surface-truth S3 가 고친 결함이 그대로 돌아온다.
    """
    existing = User(id=uuid4(), auth_subject="user_1", email="a@b.c", is_active=True)
    user_repo_mock.find_by_id.return_value = existing

    await service.deactivate_account(existing.id)

    user_repo_mock.set_inactive.assert_awaited_once_with(existing.id)
    strategy_repo_mock.archive_all_by_owner.assert_awaited_once_with(existing.id)
    user_repo_mock.commit.assert_awaited()


@pytest.mark.asyncio
async def test_deactivate_account_unknown_user_is_noop(service, user_repo_mock, strategy_repo_mock):
    """모르는 사용자면 아무것도 하지 않는다 — 커밋도 없다."""
    user_repo_mock.find_by_id.return_value = None

    await service.deactivate_account(uuid4())

    user_repo_mock.set_inactive.assert_not_awaited()
    strategy_repo_mock.archive_all_by_owner.assert_not_awaited()
    user_repo_mock.commit.assert_not_awaited()

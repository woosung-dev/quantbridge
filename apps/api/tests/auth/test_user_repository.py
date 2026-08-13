"""UserRepository 통합 테스트 (실 PostgreSQL)."""
from __future__ import annotations

import uuid

import pytest

from src.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_insert_if_absent_creates_new_user(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(clerk_id, email="a@b.com", username="alice")
    await repo.commit()

    assert user.clerk_user_id == clerk_id
    assert user.email == "a@b.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_insert_if_absent_is_idempotent(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    first = await repo.insert_if_absent(clerk_id, email="a@b.com", username="alice")
    await repo.commit()
    second = await repo.insert_if_absent(clerk_id, email="different@b.com", username="different")
    await repo.commit()

    assert first.id == second.id
    assert second.email == "a@b.com"  # 기존 값 보존 (ON CONFLICT DO NOTHING)


@pytest.mark.asyncio
async def test_find_by_clerk_id_returns_none_if_missing(db_session):
    repo = UserRepository(db_session)
    found = await repo.find_by_clerk_id("user_nonexistent")
    assert found is None


@pytest.mark.asyncio
async def test_update_profile_changes_email_and_username(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(clerk_id, email="old@b.com", username="old")
    await repo.commit()

    updated = await repo.update_profile(user.id, email="new@b.com", username="new")
    await repo.commit()

    assert updated.email == "new@b.com"
    assert updated.username == "new"


@pytest.mark.asyncio
async def test_set_inactive_soft_deletes(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(clerk_id)
    await repo.commit()

    await repo.set_inactive(user.id)
    await repo.commit()

    fetched = await repo.find_by_clerk_id(clerk_id)
    assert fetched is not None
    assert fetched.is_active is False


@pytest.mark.asyncio
async def test_upsert_from_webhook_inserts_or_updates(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"

    # 최초: INSERT
    u1 = await repo.upsert_from_webhook(
        clerk_user_id=clerk_id,
        email="first@b.com",
        username="first",
    )
    await repo.commit()
    assert u1.email == "first@b.com"

    # 두번째: UPDATE
    u2 = await repo.upsert_from_webhook(
        clerk_user_id=clerk_id,
        email="second@b.com",
        username="second",
    )
    await repo.commit()
    assert u2.id == u1.id
    assert u2.email == "second@b.com"

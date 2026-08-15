"""UserRepository 통합 테스트 (실 PostgreSQL)."""

from __future__ import annotations

import uuid
from uuid import uuid4

import pytest

from src.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_insert_if_absent_creates_new_user(db_session):
    repo = UserRepository(db_session)
    auth_subject = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(auth_subject, email="a@b.com", username="alice")
    await repo.commit()

    assert user.auth_subject == auth_subject
    assert user.email == "a@b.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_insert_if_absent_is_idempotent(db_session):
    repo = UserRepository(db_session)
    auth_subject = f"user_{uuid.uuid4().hex[:8]}"
    first = await repo.insert_if_absent(auth_subject, email="a@b.com", username="alice")
    await repo.commit()
    second = await repo.insert_if_absent(
        auth_subject, email="different@b.com", username="different"
    )
    await repo.commit()

    assert first.id == second.id
    assert second.email == "a@b.com"  # 기존 값 보존 (ON CONFLICT DO NOTHING)


@pytest.mark.asyncio
async def test_find_by_auth_subject_returns_none_if_missing(db_session):
    repo = UserRepository(db_session)
    found = await repo.find_by_auth_subject("user_nonexistent")
    assert found is None


@pytest.mark.asyncio
async def test_update_profile_changes_email_and_username(db_session):
    repo = UserRepository(db_session)
    auth_subject = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(auth_subject, email="old@b.com", username="old")
    await repo.commit()

    updated = await repo.update_profile(user.id, email="new@b.com", username="new")
    await repo.commit()

    assert updated.email == "new@b.com"
    assert updated.username == "new"


@pytest.mark.asyncio
async def test_set_inactive_soft_deletes(db_session):
    repo = UserRepository(db_session)
    auth_subject = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(auth_subject)
    await repo.commit()

    await repo.set_inactive(user.id)
    await repo.commit()

    fetched = await repo.find_by_auth_subject(auth_subject)
    assert fetched is not None
    assert fetched.is_active is False


@pytest.mark.asyncio
async def test_insert_if_absent_stores_country_code(db_session):
    """최초 프로비저닝이 JWT payload 의 국가를 함께 적는다(geo-block L3 저장 축)."""
    repo = UserRepository(db_session)
    subject = f"user_{uuid4().hex[:8]}"

    user = await repo.insert_if_absent(auth_subject=subject, email=None, country_code="KR")

    assert user.country_code == "KR"


@pytest.mark.asyncio
async def test_update_profile_does_not_erase_country_with_none(db_session):
    """★국가가 없는 토큰이 이미 적힌 값을 **지우지 않는다**.

    종전 웹훅 upsert 는 `country_code=None` 을 그대로 덮어썼다. JWT 경로는 국가가 없는 토큰이
    정상 경우(로컬 개발·헤더 없는 프록시)라 같은 규칙을 쓰면 값이 조용히 사라진다.
    """
    repo = UserRepository(db_session)
    subject = f"user_{uuid4().hex[:8]}"
    created = await repo.insert_if_absent(auth_subject=subject, email=None, country_code="KR")

    updated = await repo.update_profile(
        created.id, email="new@example.com", username="n", country_code=None
    )

    assert updated.country_code == "KR"
    assert updated.email == "new@example.com"

# UserRepository.get_created_at — Wave 0 W4 readiness gate 조회 메서드 테스트
from __future__ import annotations

from uuid import uuid4

import pytest

from src.auth.models import User
from src.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_get_created_at_returns_user_created_at(db_session) -> None:
    repo = UserRepository(db_session)
    user = User(clerk_user_id=f"clerk_{uuid4().hex}")
    db_session.add(user)
    await db_session.flush()

    got = await repo.get_created_at(user.id)

    assert got is not None
    assert got == user.created_at


@pytest.mark.asyncio
async def test_get_created_at_missing_user_returns_none(db_session) -> None:
    repo = UserRepository(db_session)
    assert await repo.get_created_at(uuid4()) is None

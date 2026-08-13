"""Trading 테스트 공통 fixture."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """강제 생성 테스트 유저 — Strategy/ExchangeAccount FK 충족용."""
    u = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def strategy(db_session: AsyncSession, user: User):
    """신호 테스트용 최소 Strategy."""
    from src.strategy.models import ParseStatus, PineVersion, Strategy
    s = Strategy(
        user_id=user.id,
        name="T7 Strategy",
        pine_source="// empty",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(s)
    await db_session.flush()
    return s

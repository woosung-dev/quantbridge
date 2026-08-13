"""conftest fixtures가 동작하는지 확인하는 smoke 테스트."""
import pytest


@pytest.mark.asyncio
async def test_db_session_usable(db_session):
    from sqlalchemy import text

    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_client_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_authed_user_persisted(db_session, authed_user):
    from sqlalchemy import select

    from src.auth.models import User

    result = await db_session.execute(
        select(User).where(User.id == authed_user.id)
    )
    assert result.scalar_one().clerk_user_id == authed_user.clerk_user_id

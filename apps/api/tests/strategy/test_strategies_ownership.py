"""Strategy 소유권 격리 — 타 사용자 전략에 접근 시 404."""
from __future__ import annotations

import uuid
from uuid import UUID

import pytest

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import CurrentUser
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _create_user(db_session, label: str) -> User:
    user = User(
        clerk_user_id=f"user_{label}_{uuid.uuid4().hex[:6]}",
        email=f"{label}@b.com",
        username=label,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_strategy(db_session, owner_id: UUID, name: str) -> Strategy:
    s = Strategy(
        user_id=owner_id,
        name=name,
        pine_source='//@version=5\nstrategy("x")',
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


def _impersonate(app, user: User) -> None:
    async def _fake() -> CurrentUser:
        return CurrentUser.model_validate(user)

    app.dependency_overrides[get_current_user] = _fake


@pytest.mark.asyncio
async def test_get_other_users_strategy_returns_404(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    bob_strategy = await _create_strategy(db_session, bob.id, "bob_strat")

    _impersonate(app, alice)
    res = await client.get(f"/api/v1/strategies/{bob_strategy.id}")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "strategy_not_found"


@pytest.mark.asyncio
async def test_update_other_users_strategy_returns_404(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    bob_strategy = await _create_strategy(db_session, bob.id, "bob_strat")

    _impersonate(app, alice)
    res = await client.put(
        f"/api/v1/strategies/{bob_strategy.id}",
        json={"name": "hijacked"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_strategy_returns_404(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    bob_strategy = await _create_strategy(db_session, bob.id, "bob_strat")

    _impersonate(app, alice)
    res = await client.delete(f"/api/v1/strategies/{bob_strategy.id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_only_returns_own_strategies(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    await _create_strategy(db_session, alice.id, "a_one")
    await _create_strategy(db_session, alice.id, "a_two")
    await _create_strategy(db_session, bob.id, "b_one")

    _impersonate(app, alice)
    res = await client.get("/api/v1/strategies")
    assert res.status_code == 200
    names = [i["name"] for i in res.json()["items"]]
    assert set(names) == {"a_one", "a_two"}

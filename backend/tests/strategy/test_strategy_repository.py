"""StrategyRepository 통합 테스트."""
from __future__ import annotations

import uuid
from uuid import UUID

import pytest

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


async def _make_user(db_session, name: str = "owner") -> User:
    user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"{name}@b.com",
        username=name,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _new_strategy(owner_id: UUID, name: str, archived: bool = False) -> Strategy:
    return Strategy(
        user_id=owner_id,
        name=name,
        pine_source='//@version=5\nstrategy("x")',
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        is_archived=archived,
    )


@pytest.mark.asyncio
async def test_create_and_find_by_id(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)

    created = await repo.create(_new_strategy(owner.id, "s1"))
    await repo.commit()

    found = await repo.find_by_id(created.id)
    assert found is not None
    assert found.name == "s1"


@pytest.mark.asyncio
async def test_find_by_id_and_owner_returns_none_for_other(db_session):
    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")
    repo = StrategyRepository(db_session)

    bob_strat = await repo.create(_new_strategy(bob.id, "bob"))
    await repo.commit()

    found = await repo.find_by_id_and_owner(bob_strat.id, owner_id=alice.id)
    assert found is None


@pytest.mark.asyncio
async def test_list_by_owner_filters_and_paginates(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)

    for i in range(5):
        await repo.create(_new_strategy(owner.id, f"s{i}"))
    await repo.create(_new_strategy(owner.id, "archived", archived=True))
    await repo.commit()

    items, total = await repo.list_by_owner(owner.id, page=1, limit=3, is_archived=False)
    assert total == 5  # archived 제외
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_by_owner_parse_status_filter(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)

    ok = _new_strategy(owner.id, "ok")
    bad = _new_strategy(owner.id, "bad")
    bad.parse_status = ParseStatus.unsupported
    await repo.create(ok)
    await repo.create(bad)
    await repo.commit()

    items, total = await repo.list_by_owner(
        owner.id, page=1, limit=20, parse_status=ParseStatus.unsupported, is_archived=False
    )
    assert total == 1
    assert items[0].name == "bad"


@pytest.mark.asyncio
async def test_update_persists_fields(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)
    s = await repo.create(_new_strategy(owner.id, "original"))
    await repo.commit()

    s.name = "renamed"
    s.parse_status = ParseStatus.unsupported
    await repo.update(s)
    await repo.commit()

    fetched = await repo.find_by_id(s.id)
    assert fetched is not None
    assert fetched.name == "renamed"
    assert fetched.parse_status == ParseStatus.unsupported


@pytest.mark.asyncio
async def test_delete_hard_removes(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)
    s = await repo.create(_new_strategy(owner.id, "doomed"))
    await repo.commit()

    await repo.delete(s.id)
    await repo.commit()

    assert await repo.find_by_id(s.id) is None


@pytest.mark.asyncio
async def test_archive_all_by_owner_bulk(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)
    for i in range(3):
        await repo.create(_new_strategy(owner.id, f"s{i}"))
    await repo.commit()

    await repo.archive_all_by_owner(owner.id)
    await repo.commit()

    _items, total = await repo.list_by_owner(owner.id, page=1, limit=20, is_archived=True)
    assert total == 3

"""ExchangeAccountRepository — save / get_by_id / list_by_user / delete."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName


async def test_save_and_get_by_id(db_session: AsyncSession, user: User):
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository

    repo = ExchangeAccountRepository(db_session)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"cipher-key",
        api_secret_encrypted=b"cipher-secret",
        label="my bybit demo",
    )
    saved = await repo.save(account)
    await repo.commit()

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.api_key_encrypted == b"cipher-key"
    assert fetched.label == "my bybit demo"


async def test_list_by_user_returns_only_owned(db_session: AsyncSession, user: User):
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository

    repo = ExchangeAccountRepository(db_session)
    mine = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"a",
        api_secret_encrypted=b"a",
    )
    await repo.save(mine)

    other_user = User(id=uuid4(), clerk_user_id="other", email="other@test.local")
    db_session.add(other_user)
    await db_session.flush()
    theirs = ExchangeAccount(
        user_id=other_user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"b",
        api_secret_encrypted=b"b",
    )
    await repo.save(theirs)
    await repo.commit()

    results = await repo.list_by_user(user.id)
    assert len(results) == 1
    assert results[0].id == mine.id


async def test_delete_by_id(db_session: AsyncSession, user: User):
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository

    repo = ExchangeAccountRepository(db_session)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"c",
        api_secret_encrypted=b"c",
    )
    await repo.save(account)
    await repo.commit()

    rowcount = await repo.delete(account.id)
    await repo.commit()
    assert rowcount == 1

    assert await repo.get_by_id(account.id) is None

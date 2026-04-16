"""ExchangeAccountService — register + get_credentials + missing account."""
from __future__ import annotations

from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.exceptions import AccountNotFound
from src.trading.models import ExchangeMode, ExchangeName
from src.trading.schemas import RegisterAccountRequest


@pytest.fixture
def crypto():
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


async def test_register_stores_encrypted_credentials(db_session, user: User, crypto):
    from src.trading.repository import ExchangeAccountRepository
    from src.trading.service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    svc = ExchangeAccountService(repo=repo, crypto=crypto)
    req = RegisterAccountRequest(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key="my-api-key",
        api_secret="my-api-secret",
        label="test",
    )
    account = await svc.register(user.id, req)
    await repo.commit()

    fetched = await repo.get_by_id(account.id)
    assert fetched is not None
    assert crypto.decrypt(fetched.api_key_encrypted) == "my-api-key"
    assert crypto.decrypt(fetched.api_secret_encrypted) == "my-api-secret"


async def test_get_credentials_for_order_returns_plaintext(db_session, user: User, crypto):
    from src.trading.repository import ExchangeAccountRepository
    from src.trading.service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    svc = ExchangeAccountService(repo=repo, crypto=crypto)
    req = RegisterAccountRequest(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key="key-123",
        api_secret="secret-456",
    )
    account = await svc.register(user.id, req)
    await repo.commit()

    creds = await svc.get_credentials_for_order(account.id)
    assert creds.api_key == "key-123"
    assert creds.api_secret == "secret-456"


async def test_get_credentials_for_missing_account_raises(db_session, user: User, crypto):
    from src.trading.repository import ExchangeAccountRepository
    from src.trading.service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    svc = ExchangeAccountService(repo=repo, crypto=crypto)

    with pytest.raises(AccountNotFound):
        await svc.get_credentials_for_order(uuid4())

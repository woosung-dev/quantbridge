"""ExchangeAccountService — register + get_credentials + missing account + fetch_balance_usdt."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.exceptions import AccountNotFound, ProviderError
from src.trading.models import ExchangeMode, ExchangeName
from src.trading.schemas import RegisterAccountRequest


@pytest.fixture
def crypto():
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


async def test_register_stores_encrypted_credentials(db_session, user: User, crypto):
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services.account_service import ExchangeAccountService

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
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services.account_service import ExchangeAccountService

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
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services.account_service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    svc = ExchangeAccountService(repo=repo, crypto=crypto)

    with pytest.raises(AccountNotFound):
        await svc.get_credentials_for_order(uuid4())


# ── Sprint 8+ fetch_balance_usdt ──────────────────────────────────────


async def _register_futures_account(
    db_session, user: User, crypto, *, mode: ExchangeMode = ExchangeMode.demo
):
    """test fixture: Bybit Futures 모드 계정 1개 저장."""
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services.account_service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    svc = ExchangeAccountService(repo=repo, crypto=crypto)
    req = RegisterAccountRequest(
        exchange=ExchangeName.bybit,
        mode=mode,
        api_key="fb-key",
        api_secret="fb-secret",
    )
    account = await svc.register(user.id, req)
    await repo.commit()
    return account, repo, svc


async def test_fetch_balance_usdt_returns_none_when_provider_not_injected(
    db_session, user: User, crypto
):
    """Provider 미주입 (기본 생성) → None. Kill Switch caller는 config fallback."""
    account, _, svc = await _register_futures_account(db_session, user, crypto)

    result = await svc.fetch_balance_usdt(account.id)

    assert result is None


async def test_fetch_balance_usdt_returns_none_for_non_bybit_account(
    db_session, user: User, crypto
):
    """OKX/Binance 등 비-Bybit 계정은 현재 지원 X — None 반환. H2+ 확장 예정."""
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services.account_service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    mock_provider = MagicMock()
    mock_provider.fetch_balance = AsyncMock()  # 호출 안 되어야 함
    svc = ExchangeAccountService(repo=repo, crypto=crypto, bybit_futures_provider=mock_provider)
    req = RegisterAccountRequest(
        exchange=ExchangeName.okx,
        mode=ExchangeMode.demo,
        api_key="k",
        api_secret="s",
        passphrase="p",  # OKX 요구사항
    )
    account = await svc.register(user.id, req)
    await repo.commit()

    result = await svc.fetch_balance_usdt(account.id)

    assert result is None
    mock_provider.fetch_balance.assert_not_awaited()


async def test_fetch_balance_usdt_returns_provider_value_for_bybit(db_session, user: User, crypto):
    """Bybit + provider 주입 → USDT free balance Decimal 반환."""
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services.account_service import ExchangeAccountService

    repo = ExchangeAccountRepository(db_session)
    mock_provider = MagicMock()
    mock_provider.fetch_balance = AsyncMock(
        return_value={"USDT": Decimal("8500.5"), "BTC": Decimal("0.1")}
    )
    svc = ExchangeAccountService(repo=repo, crypto=crypto, bybit_futures_provider=mock_provider)
    req = RegisterAccountRequest(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key="fk",
        api_secret="fs",
    )
    account = await svc.register(user.id, req)
    await repo.commit()

    result = await svc.fetch_balance_usdt(account.id)

    assert result == Decimal("8500.5")
    mock_provider.fetch_balance.assert_awaited_once()


async def test_fetch_balance_usdt_returns_none_on_provider_error(
    db_session, user: User, crypto, monkeypatch
):
    """Provider가 ProviderError 발생 시 None + warning log (trading 중단 금지).

    caplog는 다른 test의 logger 설정에 영향을 받아 전체 실행에서 불안정.
    logger.warning을 직접 monkeypatch로 가로채어 message만 검증.
    """
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.services import account_service as service_module
    from src.trading.services.account_service import ExchangeAccountService

    captured_warnings: list[str] = []

    def capture_warning(msg: str, *args, **kwargs) -> None:
        captured_warnings.append(msg)

    monkeypatch.setattr(service_module.logger, "warning", capture_warning)

    repo = ExchangeAccountRepository(db_session)
    mock_provider = MagicMock()
    mock_provider.fetch_balance = AsyncMock(side_effect=ProviderError("network timeout"))
    svc = ExchangeAccountService(repo=repo, crypto=crypto, bybit_futures_provider=mock_provider)
    req = RegisterAccountRequest(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key="ek",
        api_secret="es",
    )
    account = await svc.register(user.id, req)
    await repo.commit()

    result = await svc.fetch_balance_usdt(account.id)

    assert result is None
    assert "fetch_balance_failed" in captured_warnings

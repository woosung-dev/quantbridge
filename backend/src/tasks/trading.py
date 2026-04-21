"""execute_order_task — Celery shared_task + prefork-safe lazy init.

Task 16: pending → submitted → provider.create_order → filled/rejected.
3-guard transitions via OrderRepository (Sprint 4 패턴).

Module-level imports:
- `async_session_factory` is module-level so tests can monkeypatch it.
- `_exchange_provider` is a lazy singleton via `_get_exchange_provider()`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.trading.encryption import EncryptionService
from src.trading.exceptions import OrderNotFound, ProviderError
from src.trading.models import ExchangeAccount, OrderState
from src.trading.providers import Credentials, ExchangeProvider, OrderSubmit
from src.trading.repository import OrderRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker-local, lazy-initialized (prefork-safe)
# ---------------------------------------------------------------------------
_worker_engine = None
_sessionmaker_cache: async_sessionmaker[AsyncSession] | None = None


def async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Worker-local async_sessionmaker. Lazy init per child process.

    Tests monkeypatch this at module level:
        monkeypatch.setattr(task_mod, "async_session_factory", _FakeSM())
    """
    global _worker_engine, _sessionmaker_cache
    if _sessionmaker_cache is None:
        _worker_engine = create_async_engine(settings.database_url, echo=False)
        _sessionmaker_cache = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _sessionmaker_cache


# ---------------------------------------------------------------------------
# ExchangeProvider singleton (prefork-safe lazy init)
# ---------------------------------------------------------------------------
_exchange_provider: ExchangeProvider | None = None


def _get_exchange_provider() -> ExchangeProvider:
    """Lazy singleton — dispatches on settings.exchange_provider."""
    global _exchange_provider
    if _exchange_provider is None:
        _exchange_provider = _build_exchange_provider()
    return _exchange_provider


def _build_exchange_provider() -> ExchangeProvider:
    """Factory — settings.exchange_provider → concrete provider."""
    provider_name = settings.exchange_provider
    if provider_name == "fixture":
        from src.trading.providers import FixtureExchangeProvider

        return FixtureExchangeProvider()
    elif provider_name == "bybit_demo":
        from src.trading.providers import BybitDemoProvider

        return BybitDemoProvider()
    elif provider_name == "bybit_futures":
        # Sprint 7a: Bybit Linear Perpetual (USDT margined) testnet.
        from src.trading.providers import BybitFuturesProvider

        return BybitFuturesProvider()
    elif provider_name == "okx_demo":
        # Sprint 7d: OKX Spot sandbox via CCXT (passphrase required).
        from src.trading.providers import OkxDemoProvider

        return OkxDemoProvider()
    else:
        raise ValueError(f"Unknown exchange_provider: {provider_name}")


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------
@shared_task(name="trading.execute_order", max_retries=0)  # type: ignore[untyped-decorator]
def execute_order_task(order_id: str) -> dict[str, Any]:
    """Sync Celery entry point — asyncio.run() for prefork pool."""
    return asyncio.run(_async_execute(UUID(order_id)))


async def _async_execute(order_id: UUID) -> dict[str, Any]:
    """Core logic: pending → submitted → provider.create_order → filled/rejected.

    Returns dict with order state for Celery result backend.
    """
    sm = async_session_factory()
    async with sm() as session:
        repo = OrderRepository(session)

        # 1. Fetch order
        order = await repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        # Guard: only process pending orders
        if order.state != OrderState.pending:
            logger.warning(
                "order_not_pending",
                extra={"order_id": str(order_id), "state": order.state},
            )
            return {"order_id": str(order_id), "state": order.state, "skipped": True}

        # 2. Transition: pending → submitted
        now = datetime.now(UTC)
        rows = await repo.transition_to_submitted(order_id, submitted_at=now)
        if rows == 0:
            logger.warning(
                "concurrent_transition_submitted",
                extra={"order_id": str(order_id)},
            )
            return {"order_id": str(order_id), "state": "conflict", "skipped": True}
        await session.commit()

        # 3. Decrypt credentials
        try:
            crypto = EncryptionService(settings.trading_encryption_keys)
            account = await session.get(ExchangeAccount, order.exchange_account_id)
            if account is None:
                raise OrderNotFound(order_id)  # account missing — treat as error

            passphrase_pt = (
                crypto.decrypt(account.passphrase_encrypted)
                if account.passphrase_encrypted is not None
                else None
            )
            creds = Credentials(
                api_key=crypto.decrypt(account.api_key_encrypted),
                api_secret=crypto.decrypt(account.api_secret_encrypted),
                passphrase=passphrase_pt,
                environment=account.mode,
            )
        except Exception as e:
            error_msg = f"credential_decrypt_failed: {type(e).__name__}"
            logger.error(
                "credential_decrypt_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            await repo.transition_to_rejected(
                order_id, error_message=error_msg, failed_at=datetime.now(UTC)
            )
            await session.commit()
            return {
                "order_id": str(order_id),
                "state": "rejected",
                "error_message": error_msg,
            }

        # 4. Call exchange provider
        try:
            provider = _get_exchange_provider()
            order_submit = OrderSubmit(
                symbol=order.symbol,
                side=order.side,
                type=order.type,
                quantity=order.quantity,
                price=order.price,
                # Sprint 7a: Futures. Spot은 모두 None. DB는 str로 저장되지만
                # OrderRequest schema validator가 insert 시점에 Literal 검증 완료.
                leverage=order.leverage,
                margin_mode=order.margin_mode,  # type: ignore[arg-type]
            )
            receipt = await provider.create_order(creds, order_submit)
        except ProviderError as e:
            error_msg = f"provider_failure: {e}"
            logger.error(
                "provider_create_order_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            await repo.transition_to_rejected(
                order_id, error_message=error_msg, failed_at=datetime.now(UTC)
            )
            await session.commit()
            return {
                "order_id": str(order_id),
                "state": "rejected",
                "error_message": error_msg,
            }

        # 5. Transition: submitted → filled
        filled_at = datetime.now(UTC)
        rows = await repo.transition_to_filled(
            order_id,
            exchange_order_id=receipt.exchange_order_id,
            filled_price=receipt.filled_price,
            filled_at=filled_at,
        )
        if rows == 0:
            logger.warning(
                "concurrent_transition_filled",
                extra={"order_id": str(order_id)},
            )
            return {"order_id": str(order_id), "state": "conflict", "skipped": True}
        await session.commit()

        logger.info(
            "order_executed",
            extra={
                "order_id": str(order_id),
                "exchange_order_id": receipt.exchange_order_id,
                "filled_price": str(receipt.filled_price) if receipt.filled_price else None,
            },
        )
        return {
            "order_id": str(order_id),
            "state": "filled",
            "exchange_order_id": receipt.exchange_order_id,
            "filled_price": str(receipt.filled_price) if receipt.filled_price else None,
        }

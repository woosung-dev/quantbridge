"""BybitReconcileFetcher — CCXT 기반 REST snapshot 어댑터 (Sprint 12 Phase C).

G4 fix #11 production wiring:
- ``Reconciler`` 가 사용하는 ``ReconcileFetcher`` Protocol 의 실제 구현.
- ephemeral CCXT 인스턴스 패턴 (``BybitDemoProvider`` 와 동일) — credentials
  메모리 잔존 최소화. account_id 별로 매 호출마다 fresh client.
- ``fetch_open_orders`` + ``fetch_recent_orders`` (closed + canceled).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import ccxt.async_support as ccxt_async

from src.common.metrics import ccxt_timer
from src.trading.encryption import EncryptionService
from src.trading.models import ExchangeAccount
from src.trading.providers import _apply_bybit_env

logger = logging.getLogger(__name__)


class BybitReconcileFetcher:
    """Bybit V5 REST snapshot fetcher — Reconciler 용.

    각 fetch 호출은 ephemeral CCXT 인스턴스 (close on finally).
    account credentials 는 EncryptionService 로 in-memory decrypt.

    instance 는 단일 ExchangeAccount 에 결박. 재사용 가능 (stateless).
    """

    def __init__(
        self,
        *,
        account: ExchangeAccount,
        crypto: EncryptionService,
        category: str = "linear",
    ) -> None:
        self._account = account
        self._crypto = crypto
        # Bybit V5 category — "linear" (USDT perp), "spot", "inverse".
        # Sprint 12 dogfood: Bybit Linear Perpetual (default).
        self._category = category

    def _build_exchange(self) -> Any:
        api_key = self._crypto.decrypt(self._account.api_key_encrypted)
        api_secret = self._crypto.decrypt(self._account.api_secret_encrypted)
        exchange = ccxt_async.bybit(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {
                    "defaultType": self._category,
                    "testnet": False,
                },
            }
        )
        _apply_bybit_env(exchange, self._account.mode)
        return exchange

    async def fetch_open_orders(self, account_id: UUID) -> list[dict[str, Any]]:
        """현재 active (Bybit: New / PartiallyFilled) orders."""
        if account_id != self._account.id:
            logger.warning(
                "reconcile_fetcher_account_mismatch fetcher=%s requested=%s",
                self._account.id,
                account_id,
            )
        exchange = self._build_exchange()
        try:
            async with ccxt_timer("bybit", "fetch_open_orders"):
                # symbol=None → 모든 symbol. params={category} V5 라우팅.
                raw = await exchange.fetch_open_orders(
                    None, params={"category": self._category}
                )
            return list(raw)
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.debug("ccxt_close_failed_after_fetch_open")

    async def fetch_recent_orders(
        self, account_id: UUID, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        """최근 closed/canceled orders. Reconciler 가 terminal status 추적용."""
        if account_id != self._account.id:
            logger.warning(
                "reconcile_fetcher_account_mismatch fetcher=%s requested=%s",
                self._account.id,
                account_id,
            )
        exchange = self._build_exchange()
        try:
            async with ccxt_timer("bybit", "fetch_closed_orders"):
                raw = await exchange.fetch_closed_orders(
                    None, limit=limit, params={"category": self._category}
                )
            return list(raw)
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.debug("ccxt_close_failed_after_fetch_recent")


# Sprint 12 dogfood: 1 user x Bybit demo. mode 별 endpoint 라우팅은
# providers._apply_bybit_env 가 처리. 호출자는 BybitReconcileFetcher 인스턴스를
# _stream_main 에서 생성하여 Reconciler 에 주입.

__all__ = ["BybitReconcileFetcher"]

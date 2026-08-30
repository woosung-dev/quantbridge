# 거래소 계정별 USDT 잔고 조회와 짧은 Redis 캐시를 담당한다.
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.trading.exceptions import AccountNotFound
from src.trading.product_policy import is_bybit_demo_account
from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.schemas import AccountBalanceResponse
from src.trading.services.account_service import ExchangeAccountService

logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 15


class AccountBalanceService:
    def __init__(
        self,
        *,
        account_repo: ExchangeAccountRepository,
        account_service: ExchangeAccountService,
        bybit_futures_provider: BybitFuturesProvider,
        redis: Any,
    ) -> None:
        self._account_repo = account_repo
        self._account_service = account_service
        self._bybit_futures_provider = bybit_futures_provider
        self._redis = redis

    async def get_balance(
        self, user_id: UUID, account_id: UUID, *, force_refresh: bool = False
    ) -> AccountBalanceResponse:
        """USDT 잔고 조회. 기본은 15초 캐시.

        BL-479 — `force_refresh=True` 는 캐시를 건너뛰고 거래소를 직접 친다. 라이브 세션
        기준선처럼 **한 번 찍으면 세션 내내 남는 값**은 15초 stale 을 영구히 물려받으면
        안 된다(입금 직후 시작하면 입금 전 잔고로 세션 전체를 사이징한다). 갱신한 값은
        캐시에도 다시 써서 뒤따르는 조회가 이득을 본다.
        """
        account = await self._account_repo.get_by_id(account_id)
        if account is None or account.user_id != user_id:
            raise AccountNotFound(account_id)
        # legacy live/OKX 행은 목록·삭제용으로 보존한다. 캐시 hit도 private API의
        # 현재 상태로 오해되지 않게, cache/key/credential 처리 전에 지원 밖으로 끝낸다.
        if not is_bybit_demo_account(account.exchange, account.mode):
            return AccountBalanceResponse(
                account_id=account_id,
                asset="USDT",
                supported=False,
                reason="bybit_demo_only",
                total=None,
                free=None,
                fetched_at=None,
            )

        cache_key = f"qb_balance_snapshot:{account_id}"
        if not force_refresh:
            cached = await self._read_cache(cache_key)
            if cached is not None:
                total, free, fetched_at = cached
                return self._response(account_id, total, free, fetched_at)

        credentials = await self._account_service.get_credentials_for_order(account_id)
        snapshot = await self._bybit_futures_provider.fetch_usdt_balance_snapshot(credentials)
        fetched_at = datetime.now(UTC)
        await self._write_cache(cache_key, snapshot.total, snapshot.free, fetched_at)
        return self._response(account_id, snapshot.total, snapshot.free, fetched_at)

    async def _read_cache(
        self, cache_key: str
    ) -> tuple[Decimal | None, Decimal | None, datetime] | None:
        try:
            raw = await self._redis.get(cache_key)
            if raw is None:
                return None
            decoded = raw.decode() if isinstance(raw, bytes) else raw
            payload = json.loads(decoded)
            fetched_at = datetime.fromisoformat(payload["fetched_at"])
            if fetched_at.tzinfo is None:
                return None
            return (
                self._decimal_or_none(payload["total"]),
                self._decimal_or_none(payload["free"]),
                fetched_at,
            )
        except Exception as exc:
            logger.warning(
                "balance_snapshot_cache_read_failed", extra={"error": type(exc).__name__}
            )
            return None

    async def _write_cache(
        self,
        cache_key: str,
        total: Decimal | None,
        free: Decimal | None,
        fetched_at: datetime,
    ) -> None:
        payload = {
            "total": self._decimal_string(total),
            "free": self._decimal_string(free),
            "fetched_at": fetched_at.isoformat(),
        }
        try:
            await self._redis.set(cache_key, json.dumps(payload), ex=_CACHE_TTL_SECONDS)
        except Exception as exc:  # 캐시 장애는 거래소 잔고 조회를 막지 않는다.
            logger.warning(
                "balance_snapshot_cache_write_failed", extra={"error": type(exc).__name__}
            )

    @staticmethod
    def _response(
        account_id: UUID, total: Decimal | None, free: Decimal | None, fetched_at: datetime
    ) -> AccountBalanceResponse:
        return AccountBalanceResponse(
            account_id=account_id,
            asset="USDT",
            supported=True,
            reason=None,
            total=total,
            free=free,
            fetched_at=fetched_at,
        )

    @staticmethod
    def _decimal_or_none(value: object) -> Decimal | None:
        if value is None:
            return None
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("non-finite cached balance")
        return result

    @staticmethod
    def _decimal_string(value: Decimal | None) -> str | None:
        return str(value) if value is not None else None

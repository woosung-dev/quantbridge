# trading service — ExchangeAccount CRUD + AES-256 암호화 단독 책임

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from src.trading.encryption import EncryptionService
from src.trading.exceptions import AccountNotFound, ProviderError
from src.trading.models import ExchangeAccount
from src.trading.providers import BybitFuturesProvider, Credentials
from src.trading.repository import ExchangeAccountRepository
from src.trading.schemas import RegisterAccountRequest

logger = logging.getLogger(__name__)


class ExchangeAccountService:
    def __init__(
        self,
        repo: ExchangeAccountRepository,
        crypto: EncryptionService,
        bybit_futures_provider: BybitFuturesProvider | None = None,
    ) -> None:
        self._repo = repo
        self._crypto = crypto
        self._bybit_futures_provider = bybit_futures_provider

    async def register(self, user_id: UUID, req: RegisterAccountRequest) -> ExchangeAccount:
        # Sprint 7d: passphrase는 선택적. 존재 시 동일 AES-256 레이어로 암호화.
        passphrase_ct = self._crypto.encrypt(req.passphrase) if req.passphrase else None
        account = ExchangeAccount(
            user_id=user_id,
            exchange=req.exchange,
            mode=req.mode,
            api_key_encrypted=self._crypto.encrypt(req.api_key),
            api_secret_encrypted=self._crypto.encrypt(req.api_secret),
            passphrase_encrypted=passphrase_ct,
            label=req.label,
        )
        saved = await self._repo.save(account)
        # Sprint 15-A: commit 누락 fix. Sprint 6 (webhook_secret) / Sprint 13 (OrderService)
        # 와 동일 broken bug 3 번째 재발 — get_async_session() 자동 commit 안 함이라
        # request 종료 시 ROLLBACK. 회귀 테스트 test_register_calls_repo_commit.
        await self._repo.commit()
        return saved

    async def get_credentials_for_order(self, account_id: UUID) -> Credentials:
        """Provider가 주문 직전에만 호출. 감사 로깅 포인트."""
        account = await self._repo.get_by_id(account_id)
        if account is None:
            raise AccountNotFound(account_id)
        logger.info(
            "trading_credentials_decrypted",
            extra={
                "account_id": str(account_id),
                "exchange": account.exchange.value,
                "mode": account.mode.value,
                "purpose": "order_execution",
            },
        )
        passphrase_pt = (
            self._crypto.decrypt(account.passphrase_encrypted)
            if account.passphrase_encrypted is not None
            else None
        )
        return Credentials(
            api_key=self._crypto.decrypt(account.api_key_encrypted),
            api_secret=self._crypto.decrypt(account.api_secret_encrypted),
            passphrase=passphrase_pt,
            environment=account.mode,
        )

    async def fetch_balance_usdt(self, account_id: UUID) -> Decimal | None:
        """계좌 USDT 자유잔고 조회. Sprint 8+ Kill Switch capital_base 동적 바인딩.

        현재 구현: Bybit 거래소 계정만 Linear Perp 잔고 조회. OKX / Binance는 H2+ 확장.
        ExchangeMode는 환경 구분(demo/live)이라 Futures/Spot 판단에 사용 X —
        provider 선택으로만 분기한다. 계정당 Futures/Spot 배타 사용이 규약.

        반환 None 조건 (fallback 경로):
        - 계좌 미발견
        - 비-Bybit 계좌 (OKX/Binance는 H2+)
        - Provider 미주입 (테스트/CI 환경)
        - Provider 호출 실패 (네트워크/API 에러 — 경고 로깅)

        H1 Stealth 기간에는 매 호출마다 CCXT fetch_balance (~200ms).
        TTL cache는 H2+에서 WebSocket 스트리밍으로 대체 예정.
        """
        account = await self._repo.get_by_id(account_id)
        if account is None:
            return None
        if self._bybit_futures_provider is None or account.exchange.value != "bybit":
            return None
        creds = await self.get_credentials_for_order(account_id)
        try:
            balances = await self._bybit_futures_provider.fetch_balance(creds)
        except ProviderError as exc:
            logger.warning(
                "fetch_balance_failed",
                extra={"account_id": str(account_id), "error": str(exc)},
            )
            return None
        return balances.get("USDT")

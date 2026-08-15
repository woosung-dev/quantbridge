# trading service — ExchangeAccount CRUD + AES-256 암호화 단독 책임

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from src.trading.encryption import EncryptionService
from src.trading.exceptions import AccountNotFound, ProviderError
from src.trading.models import ExchangeAccount, ExchangeName
from src.trading.providers import BybitFuturesProvider, Credentials
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.schemas import RegisterAccountRequest, mask_api_key

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
        await self._populate_exchange_identity(saved)
        # Sprint 15-A: commit 누락 fix. Sprint 6 (webhook_secret) / Sprint 13 (OrderService)
        # 와 동일 broken bug 3 번째 재발 — get_async_session() 자동 commit 안 함이라
        # request 종료 시 ROLLBACK. 회귀 테스트 test_register_calls_repo_commit.
        await self._repo.commit()
        return saved

    # ── 라우터가 `_repo`·`_crypto` 를 뚫지 않게 하는 공개 표면 ([BL-762], 2026-08-16) ──
    #
    # ★종전 `trading/router.py` 는 이 세 endpoint 에서 `svc._repo` 를 5곳, `svc._crypto` 를
    #   2곳 직접 만졌다. 그 경로에는 **LESSON-019 commit-spy 를 붙일 수 없다** — 커밋을 치는
    #   것이 서비스가 아니라 라우터라 spy 가 볼 대상이 없다. 트랜잭션 경계와 소유권 검사를
    #   서비스로 되돌려 그 회귀 테스트가 성립하게 만든다(`AGENTS.md` §3).

    async def list_for_user(self, user_id: UUID) -> Sequence[ExchangeAccount]:
        return await self._repo.list_by_user(user_id)

    async def delete_for_user(self, account_id: UUID, user_id: UUID) -> None:
        """소유권 검사 + 삭제 + 커밋을 한 경계 안에 둔다.

        ★소유권 검사를 여기서 하는 이유 — 라우터에 두면 `delete_for_user` 를 다른 호출자가
        재사용할 때 검사가 조용히 빠진다. 남의 계정은 존재를 알리지 않기 위해
        `AccountNotFound`(404) 로 답한다 — 종전 라우터 동작과 같다.
        """
        account = await self._repo.get_by_id(account_id)
        if account is None or account.user_id != user_id:
            raise AccountNotFound(account_id)
        await self._repo.delete(account_id)
        await self._repo.commit()

    def masked_api_key(self, account: ExchangeAccount) -> str:
        """평문 키는 저장하지 않으므로 마스킹에 복호화가 선행한다 — 그 복호화는 서비스가 소유한다."""
        return mask_api_key(self._crypto.decrypt(account.api_key_encrypted))

    async def backfill_exchange_identities(self) -> dict[str, int]:
        """UID가 아직 없는 계정만 식별해 채운다. 실패는 다음 beat에 재시도한다."""
        accounts = await self._repo.list_without_exchange_uid()
        updated = 0
        for account in accounts:
            if await self._populate_exchange_identity(account):
                updated += 1
        if updated:
            await self._repo.commit()
        return {"scanned": len(accounts), "updated": updated}

    async def _populate_exchange_identity(self, account: ExchangeAccount) -> bool:
        if (
            account.exchange != ExchangeName.bybit
            or account.exchange_uid is not None
            or self._bybit_futures_provider is None
        ):
            return False
        try:
            exchange_uid, read_only = await self._bybit_futures_provider.fetch_api_identity(
                self._credentials_for(account)
            )
        except Exception as exc:
            logger.warning(
                "exchange_account_identity_fetch_failed",
                extra={"account_id": str(account.id), "error": type(exc).__name__},
            )
            return False
        account.exchange_uid = exchange_uid
        account.read_only = read_only
        return True

    def _credentials_for(self, account: ExchangeAccount) -> Credentials:
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
        return self._credentials_for(account)

    async def fetch_mark_price(self, account_id: UUID, symbol: str) -> Decimal | None:
        """P1-13 (S5-B): market order notional 근사 가드용 mark price 조회.

        반환 None 조건 (fail-soft, caller fallback 결정):
        - 계좌 미발견 / 비-Bybit / Provider 미주입 (테스트/CI)
        - Provider 호출 실패 (네트워크/API 에러)
        - ticker 에서 mark/last/close 추출 실패
        """
        account = await self._repo.get_by_id(account_id)
        if account is None:
            return None
        if self._bybit_futures_provider is None or account.exchange.value != "bybit":
            return None
        creds = await self.get_credentials_for_order(account_id)
        try:
            return await self._bybit_futures_provider.fetch_mark_price(creds, symbol)
        except ProviderError as exc:
            logger.warning(
                "fetch_mark_price_failed",
                extra={
                    "account_id": str(account_id),
                    "symbol": symbol,
                    "error": str(exc),
                },
            )
            return None

    async def fetch_min_notional(self, account_id: UUID, symbol: str) -> Decimal | None:
        """Wave 1 C5 — 심볼의 거래소 최소 주문 cost 조회 (min-notional 가드용).

        반환 None 조건 (fail-soft, caller fail-open skip):
        - 계좌 미발견 / 비-Bybit / Provider 미주입 (테스트/CI)
        - Provider 호출 실패 또는 limits.cost.min 메타 미가용
        """
        account = await self._repo.get_by_id(account_id)
        if account is None:
            return None
        if self._bybit_futures_provider is None or account.exchange.value != "bybit":
            return None
        creds = await self.get_credentials_for_order(account_id)
        try:
            return await self._bybit_futures_provider.fetch_min_notional(creds, symbol)
        except ProviderError as exc:
            logger.warning(
                "fetch_min_notional_failed",
                extra={"account_id": str(account_id), "symbol": symbol, "error": str(exc)},
            )
            return None

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

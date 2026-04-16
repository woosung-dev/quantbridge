"""trading Service. 비즈니스 로직 + 트랜잭션 경계. AsyncSession import 절대 금지."""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from uuid import UUID

from src.trading.encryption import EncryptionService
from src.trading.exceptions import AccountNotFound
from src.trading.models import ExchangeAccount, WebhookSecret
from src.trading.providers import Credentials
from src.trading.repository import ExchangeAccountRepository, WebhookSecretRepository
from src.trading.schemas import RegisterAccountRequest

logger = logging.getLogger(__name__)


class ExchangeAccountService:
    def __init__(
        self,
        repo: ExchangeAccountRepository,
        crypto: EncryptionService,
    ) -> None:
        self._repo = repo
        self._crypto = crypto

    async def register(
        self, user_id: UUID, req: RegisterAccountRequest
    ) -> ExchangeAccount:
        account = ExchangeAccount(
            user_id=user_id,
            exchange=req.exchange,
            mode=req.mode,
            api_key_encrypted=self._crypto.encrypt(req.api_key),
            api_secret_encrypted=self._crypto.encrypt(req.api_secret),
            label=req.label,
        )
        return await self._repo.save(account)

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
        return Credentials(
            api_key=self._crypto.decrypt(account.api_key_encrypted),
            api_secret=self._crypto.decrypt(account.api_secret_encrypted),
        )


class WebhookSecretService:
    """CSO-1: webhook secret은 EncryptionService로 암호화 저장.

    - issue(): plaintext 생성 -> encrypt -> DB bytes 저장 -> plaintext 반환 (URL 표시용)
    - rotate(): 기존 일괄 revoke -> 신규 issue
    - verify 경로 (T17): DB에서 encrypted 로드 -> decrypt -> HMAC compare
    """

    def __init__(
        self,
        repo: WebhookSecretRepository,
        crypto: EncryptionService,  # CSO-1: plan에서 누락됐지만 audit에서 필수 명시
    ) -> None:
        self._repo = repo
        self._crypto = crypto

    async def issue(self, strategy_id: UUID) -> str:
        """최초 secret 발급. plaintext 반환 (호출자에게 1회 표시)."""
        plaintext = secrets.token_urlsafe(32)
        encrypted = self._crypto.encrypt(plaintext)
        await self._repo.save(
            WebhookSecret(strategy_id=strategy_id, secret_encrypted=encrypted)
        )
        return plaintext

    async def rotate(self, strategy_id: UUID, *, grace_period_seconds: int) -> str:
        """신규 secret 발급 + 기존 일괄 revoke. grace 내엔 구 secret도 검증 통과."""
        now = datetime.now(UTC)
        await self._repo.revoke_all_active(strategy_id, at=now)
        plaintext = secrets.token_urlsafe(32)
        encrypted = self._crypto.encrypt(plaintext)
        await self._repo.save(
            WebhookSecret(strategy_id=strategy_id, secret_encrypted=encrypted)
        )
        logger.info(
            "webhook_secret_rotated",
            extra={"strategy_id": str(strategy_id), "grace_seconds": grace_period_seconds},
        )
        return plaintext

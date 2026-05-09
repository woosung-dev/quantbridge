# trading service — webhook HMAC secret 단독 책임

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from uuid import UUID

from src.trading.encryption import EncryptionService
from src.trading.models import WebhookSecret
from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

logger = logging.getLogger(__name__)


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

    async def issue(self, strategy_id: UUID, *, commit: bool = True) -> str:
        """최초 secret 발급. plaintext 반환 (호출자에게 1회 표시).

        Sprint 13 Phase A.1.1: commit 누락이 dogfood Day 1 에서 webhook_secrets 0건의
        root cause 였다. default=True 로 standalone 호출 시 즉시 영구 저장.

        Args:
            commit: True (default) — standalone 호출 시 즉시 commit. False — atomic 트랜잭션
                안에서 caller (e.g. StrategyService.create) 가 마지막에 한 번 commit.
        """
        plaintext = secrets.token_urlsafe(32)
        encrypted = self._crypto.encrypt(plaintext)
        await self._repo.save(WebhookSecret(strategy_id=strategy_id, secret_encrypted=encrypted))
        if commit:
            await self._repo.commit()
        return plaintext

    async def rotate(self, strategy_id: UUID, *, grace_period_seconds: int) -> str:
        """신규 secret 발급 + 기존 일괄 revoke. grace 내엔 구 secret도 검증 통과.

        Sprint 13 Phase A.1.1: commit 누락 hotfix. 기존 Sprint 6 구현은 plaintext 반환만
        하고 DB 저장은 request 종료 시 rollback 되어 webhook_secrets 0건 root cause.
        """
        now = datetime.now(UTC)
        await self._repo.revoke_all_active(strategy_id, at=now)
        plaintext = secrets.token_urlsafe(32)
        encrypted = self._crypto.encrypt(plaintext)
        await self._repo.save(WebhookSecret(strategy_id=strategy_id, secret_encrypted=encrypted))
        await self._repo.commit()  # Sprint 13 Phase A.1.1 — Sprint 6 broken bug fix
        logger.info(
            "webhook_secret_rotated",
            extra={"strategy_id": str(strategy_id), "grace_seconds": grace_period_seconds},
        )
        return plaintext

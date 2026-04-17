"""Webhook HMAC 검증 + TV payload 파싱.

CSO-1: secret은 DB에서 암호화 저장 (secret_encrypted: bytes).
verify 시 EncryptionService.decrypt로 평문 복원 후 HMAC 비교.
Grace period 내 구 secret도 허용 (spec §2.4 rotation 정책).
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from src.trading.encryption import EncryptionService
from src.trading.exceptions import WebhookUnauthorized
from src.trading.models import OrderSide, OrderType
from src.trading.repository import WebhookSecretRepository


@dataclass(frozen=True, slots=True)
class ParsedTradeSignal:
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None


class WebhookService:
    def __init__(
        self,
        repo: WebhookSecretRepository,
        crypto: EncryptionService,  # CSO-1: decrypt path
        *,
        grace_seconds: int,
    ) -> None:
        self._repo = repo
        self._crypto = crypto
        self._grace = timedelta(seconds=grace_seconds)

    async def verify(
        self, strategy_id: UUID, *, token: str, payload: bytes
    ) -> bool:
        """grace_cutoff 이후 revoked된 secret까지 후보 포함.

        CSO-1: 각 candidate를 decrypt 후 HMAC compare_digest.
        """
        grace_cutoff = datetime.now(UTC) - self._grace
        candidates = await self._repo.list_valid_secrets(
            strategy_id, grace_cutoff=grace_cutoff
        )
        for ws in candidates:
            plaintext_secret = self._crypto.decrypt(ws.secret_encrypted)
            expected = hmac.new(
                plaintext_secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(expected, token):
                return True
        return False

    async def ensure_authorized(
        self, strategy_id: UUID, *, token: str, payload: bytes
    ) -> None:
        if not await self.verify(strategy_id, token=token, payload=payload):
            raise WebhookUnauthorized("Invalid HMAC token or strategy_id")


def parse_tv_payload(payload: dict[str, object]) -> ParsedTradeSignal:
    """TradingView alert payload -> 표준 signal. 필수 필드: symbol, side, quantity, type."""
    try:
        return ParsedTradeSignal(
            symbol=str(payload["symbol"]),
            side=OrderSide(str(payload["side"]).lower()),
            type=OrderType(str(payload.get("type", "market")).lower()),
            quantity=Decimal(str(payload["quantity"])),
            price=Decimal(str(payload["price"])) if payload.get("price") else None,
        )
    except (KeyError, ValueError, TypeError) as e:
        raise WebhookUnauthorized(f"Invalid TV payload: {e}") from e

"""trading Service. 비즈니스 로직 + 트랜잭션 경계.

AsyncSession import 절대 금지 — OrderService.execute advisory lock 경로만 예외.
동일 트랜잭션에서 advisory lock + 쿼리가 필요하므로 예외적 주입.
"""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,  # 예외적 주입 — OrderService.execute advisory lock 전용
)

from src.core.config import settings
from src.trading.encryption import EncryptionService
from src.trading.exceptions import (
    AccountNotFound,
    IdempotencyConflict,
    LeverageCapExceeded,
)
from src.trading.kill_switch import KillSwitchService
from src.trading.models import ExchangeAccount, Order, OrderState, WebhookSecret
from src.trading.providers import Credentials
from src.trading.repository import (
    ExchangeAccountRepository,
    OrderRepository,
    WebhookSecretRepository,
)
from src.trading.schemas import OrderRequest, OrderResponse, RegisterAccountRequest

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


class OrderDispatcher(Protocol):
    async def dispatch_order_execution(self, order_id: UUID) -> None: ...


class OrderService:
    """주문 생성 경로. Celery dispatch는 반드시 commit 이후 (visibility race 방지).

    E9: kill_switch.ensure_not_gated — begin_nested 내부, advisory lock 이후, INSERT 이전.
    E2: body_hash — 동일 idempotency_key + 다른 payload → IdempotencyConflict.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: OrderRepository,
        dispatcher: OrderDispatcher,
        kill_switch: KillSwitchService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._dispatcher = dispatcher
        self._kill_switch = kill_switch

    async def execute(
        self,
        req: OrderRequest,
        *,
        idempotency_key: str | None,
        body_hash: bytes | None = None,
    ) -> tuple[OrderResponse, bool]:
        """Returns (response, is_replayed).

        Flow (autoplan E9 + E2):
        1. leverage cap 가드 (Sprint 7a 서비스 계층 enforcement)
        2. begin_nested() — advisory lock + gate + insert 동일 tx
        3. idempotency 경로: lock → existing 확인 → hash 비교 → gate → INSERT
        4. commit 후 Celery dispatch (visibility race 방지)
        """
        # Sprint 7a: OrderRequest.leverage Field(le=125)는 Bybit 이론 상한.
        # 운영 리스크 관리용 동적 cap은 서비스 계층에서 enforce (4/4 리뷰 컨센서스).
        if req.leverage is not None and req.leverage > settings.bybit_futures_max_leverage:
            raise LeverageCapExceeded(
                requested=req.leverage,
                cap=settings.bybit_futures_max_leverage,
            )

        created_order_id: UUID | None = None
        cached_response: OrderResponse | None = None

        async with self._session.begin_nested():
            if idempotency_key is not None:
                await self._repo.acquire_idempotency_lock(idempotency_key)
                existing = await self._repo.get_by_idempotency_key(idempotency_key)
                if existing:
                    if body_hash is not None and existing.idempotency_payload_hash != body_hash:
                        raise IdempotencyConflict(
                            f"Idempotency-Key 재사용됐지만 payload가 다름. "
                            f"original_order_id={existing.id}",
                            original_order_id=existing.id,
                        )
                    cached_response = OrderResponse.model_validate(existing)
                else:
                    await self._kill_switch.ensure_not_gated(
                        strategy_id=req.strategy_id,
                        account_id=req.exchange_account_id,
                    )
                    order = await self._repo.save(Order(
                        strategy_id=req.strategy_id,
                        exchange_account_id=req.exchange_account_id,
                        symbol=req.symbol,
                        side=req.side,
                        type=req.type,
                        quantity=req.quantity,
                        price=req.price,
                        state=OrderState.pending,
                        idempotency_key=idempotency_key,
                        idempotency_payload_hash=body_hash,
                        # Sprint 7a: Futures. Spot은 모두 None.
                        leverage=req.leverage,
                        margin_mode=req.margin_mode,
                    ))
                    created_order_id = order.id
            else:
                await self._kill_switch.ensure_not_gated(
                    strategy_id=req.strategy_id,
                    account_id=req.exchange_account_id,
                )
                order = await self._repo.save(Order(
                    strategy_id=req.strategy_id,
                    exchange_account_id=req.exchange_account_id,
                    symbol=req.symbol,
                    side=req.side,
                    type=req.type,
                    quantity=req.quantity,
                    price=req.price,
                    state=OrderState.pending,
                    idempotency_key=None,
                    idempotency_payload_hash=None,
                    # Sprint 7a: Futures. Spot은 모두 None.
                    leverage=req.leverage,
                    margin_mode=req.margin_mode,
                ))
                created_order_id = order.id
        # context exit -> commit (lock 해제, row visible)

        if cached_response is not None:
            return cached_response, True

        if created_order_id is None:
            raise RuntimeError("OrderService bug: created_order_id is None after insert")
        await self._dispatcher.dispatch_order_execution(created_order_id)
        fetched = await self._repo.get_by_id(created_order_id)
        if fetched is None:
            raise RuntimeError(f"OrderService bug: order {created_order_id} not found after commit")
        return OrderResponse.model_validate(fetched), False

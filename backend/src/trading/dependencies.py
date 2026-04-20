"""trading Depends() 조립. service.py / repository.py 에서 Depends import 금지.

T18: 전체 DI factory 등록 — ExchangeAccount / Webhook / Order / KillSwitch.
CSO-1: WebhookSecretService, WebhookService에 crypto 주입 (감사 보정).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.core.config import settings
from src.strategy.models import Strategy
from src.trading.encryption import EncryptionService
from src.trading.kill_switch import (
    CumulativeLossEvaluator,
    DailyLossEvaluator,
    KillSwitchEvaluator,
    KillSwitchService,
)
from src.trading.providers import BybitFuturesProvider
from src.trading.repository import (
    ExchangeAccountRepository,
    KillSwitchEventRepository,
    OrderRepository,
    WebhookSecretRepository,
)
from src.trading.service import (
    ExchangeAccountService,
    OrderDispatcher,
    OrderService,
    WebhookSecretService,
)
from src.trading.webhook import WebhookService


# ── EncryptionService (singleton per-request) ────────────────────────
def get_encryption_service() -> EncryptionService:
    return EncryptionService(settings.trading_encryption_keys)


# ── BybitFuturesProvider (module-level singleton, stateless) ─────────
# 주문 경로는 `OrderDispatcher → Celery task`에서 별도 인스턴스 사용.
# 여기 singleton은 fetch_balance 같은 lightweight 조회용 (ExchangeAccountService 주입).
_bybit_futures_provider = BybitFuturesProvider()


def get_bybit_futures_provider() -> BybitFuturesProvider:
    return _bybit_futures_provider


# ── ExchangeAccount ──────────────────────────────────────────────────
async def get_exchange_account_service(
    session: AsyncSession = Depends(get_async_session),
    crypto: EncryptionService = Depends(get_encryption_service),
    bybit_futures_provider: BybitFuturesProvider = Depends(get_bybit_futures_provider),
) -> ExchangeAccountService:
    repo = ExchangeAccountRepository(session)
    return ExchangeAccountService(
        repo=repo,
        crypto=crypto,
        bybit_futures_provider=bybit_futures_provider,
    )


# ── WebhookSecret ────────────────────────────────────────────────────
async def get_webhook_secret_service(
    session: AsyncSession = Depends(get_async_session),
    crypto: EncryptionService = Depends(get_encryption_service),
) -> WebhookSecretService:
    repo = WebhookSecretRepository(session)
    return WebhookSecretService(repo=repo, crypto=crypto)  # CSO-1 correction


# ── Webhook (HMAC verify + TV parse) ─────────────────────────────────
async def get_webhook_service(
    session: AsyncSession = Depends(get_async_session),
    crypto: EncryptionService = Depends(get_encryption_service),
) -> WebhookService:
    repo = WebhookSecretRepository(session)
    return WebhookService(
        repo=repo,
        crypto=crypto,  # CSO-1 correction
        grace_seconds=settings.webhook_secret_grace_seconds,
    )


# ── KillSwitch ───────────────────────────────────────────────────────
async def get_kill_switch_service(
    session: AsyncSession = Depends(get_async_session),
    exchange_service: ExchangeAccountService = Depends(get_exchange_account_service),
) -> KillSwitchService:
    order_repo = OrderRepository(session)
    events_repo = KillSwitchEventRepository(session)
    evaluators: list[KillSwitchEvaluator] = [
        CumulativeLossEvaluator(
            order_repo,
            threshold_percent=settings.kill_switch_cumulative_loss_percent,
            capital_base=settings.kill_switch_capital_base_usd,
            # Sprint 8+ 동적 바인딩: ExchangeAccountService가 BalanceProvider Protocol 충족.
            # config capital_base는 fetch 실패 시 fallback.
            balance_provider=exchange_service,
        ),
        DailyLossEvaluator(
            order_repo,
            threshold_usd=settings.kill_switch_daily_loss_usd,
        ),
    ]
    return KillSwitchService(evaluators=evaluators, events_repo=events_repo)


# ── OrderDispatcher (Celery) ─────────────────────────────────────────
class _CeleryOrderDispatcher:
    async def dispatch_order_execution(self, order_id: UUID) -> None:
        from src.tasks.trading import execute_order_task

        execute_order_task.delay(str(order_id))


def get_order_dispatcher() -> OrderDispatcher:
    return _CeleryOrderDispatcher()


# ── StrategySessionsPort (Sprint 7d) ─────────────────────────────────
class _StrategySessionsAdapter:
    """StrategySessionsPort 구현 — Strategy row를 로드하고 trading_sessions만 추출.

    trading_sessions 컬럼은 nullable이므로 NULL(pre-migration rows) → []로 정규화.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_sessions(self, strategy_id: UUID) -> list[str]:
        stmt = select(Strategy).where(Strategy.id == strategy_id)  # type: ignore[arg-type]
        result = await self._session.execute(stmt)
        strategy = result.scalar_one_or_none()
        if strategy is None or strategy.trading_sessions is None:
            return []
        return list(strategy.trading_sessions)


# ── OrderService ─────────────────────────────────────────────────────
async def get_order_service(
    session: AsyncSession = Depends(get_async_session),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    dispatcher: OrderDispatcher = Depends(get_order_dispatcher),
    exchange_service: ExchangeAccountService = Depends(get_exchange_account_service),
) -> OrderService:
    repo = OrderRepository(session)
    return OrderService(
        session=session,
        repo=repo,
        dispatcher=dispatcher,
        kill_switch=kill_switch,
        sessions_port=_StrategySessionsAdapter(session),
        # Sprint 8+ notional check: qty x price x leverage ≤ available x max_leverage x 0.95
        exchange_service=exchange_service,
    )

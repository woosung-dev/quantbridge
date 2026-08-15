"""trading Depends() 조립. service.py / repository.py 에서 Depends import 금지.

T18: 전체 DI factory 등록 — ExchangeAccount / Webhook / Order / KillSwitch.
CSO-1: WebhookSecretService, WebhookService에 crypto 주입 (감사 보정).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import UserRepository
from src.common.database import get_async_session
from src.common.redis_client import get_redis_lock_pool
from src.core.config import settings
from src.strategy.models import Strategy
from src.strategy.repository import StrategyRepository
from src.trading.encryption import EncryptionService
from src.trading.kill_switch import (
    CumulativeLossEvaluator,
    DailyLossEvaluator,
    KillSwitchEvaluator,
    KillSwitchService,
)
from src.trading.outcome_parity_service import OutcomeParityService
from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.alert_rule_repository import AlertRuleRepository
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.repositories.parity_repository import ParityRepository
from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
from src.trading.services.account_exclusivity import AccountExclusivityService
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.alert_rule_service import AlertRuleService
from src.trading.services.balance_service import AccountBalanceService
from src.trading.services.close_service import ClosePositionService
from src.trading.services.liquidation_service import LiquidationService
from src.trading.services.live_session_service import LiveSignalSessionService
from src.trading.services.order_service import OrderService
from src.trading.services.position_service import PositionService
from src.trading.services.protocols import OrderDispatcher
from src.trading.services.webhook_secret_service import WebhookSecretService
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


# ── Liquidation (순수 calc, DB 미접근) ────────────────────────────────
def get_liquidation_service() -> LiquidationService:
    return LiquidationService()


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
        # BL-474 — webhook ingress 도 Strategy.settings 에서 leverage/margin_mode 를
        # 해결한다. 동일 session 주입 (LESSON-019 단일 트랜잭션).
        strategy_repo=StrategyRepository(session),
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

    async def get_owner(self, strategy_id: UUID) -> UUID | None:
        """TRD-4 — strategy 소유자(user_id) 반환. 없으면 None."""
        stmt = select(Strategy).where(Strategy.id == strategy_id)  # type: ignore[arg-type]
        result = await self._session.execute(stmt)
        strategy = result.scalar_one_or_none()
        return strategy.user_id if strategy is not None else None

    async def is_owner_active(self, user_id: UUID) -> bool:
        """2026-08-15 surface-truth (S3) — 소유자가 탈퇴했으면 주문을 막는다.

        행이 없으면 False (fail-closed) — 「모르면 보낸다」가 이 도메인에서 가장 비싼 기본값이다.
        """
        from src.auth.models import User

        stmt = select(User.is_active).where(User.id == user_id)  # type: ignore[arg-type]
        result = await self._session.execute(stmt)
        return bool(result.scalar_one_or_none())


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


# ── AccountBalance ───────────────────────────────────────────────────
async def get_balance_service(
    session: AsyncSession = Depends(get_async_session),
    account_service: ExchangeAccountService = Depends(get_exchange_account_service),
    bybit_futures_provider: BybitFuturesProvider = Depends(get_bybit_futures_provider),
) -> AccountBalanceService:
    return AccountBalanceService(
        account_repo=ExchangeAccountRepository(session),
        account_service=account_service,
        bybit_futures_provider=bybit_futures_provider,
        redis=get_redis_lock_pool(),
    )


# ── Sprint 26: LiveSignalSessionService ──────────────────────────────
async def get_live_signal_session_service(
    session: AsyncSession = Depends(get_async_session),
    balance_service: AccountBalanceService = Depends(get_balance_service),
    account_service: ExchangeAccountService = Depends(get_exchange_account_service),
    bybit_futures_provider: BybitFuturesProvider = Depends(get_bybit_futures_provider),
) -> LiveSignalSessionService:
    """Sprint 26 — Live Signal Auto-Trading session 등록/조회/종료.

    동일 session 으로 LiveSignalSessionRepository + ExchangeAccountRepository +
    StrategyRepository 주입 — 단일 트랜잭션 commit 보장 (LESSON-019 cross-repo 패턴).
    """
    return LiveSignalSessionService(
        repo=LiveSignalSessionRepository(session),
        account_repo=ExchangeAccountRepository(session),
        strategy_repo=StrategyRepository(session),
        balance_service=balance_service,
        exclusivity_service=AccountExclusivityService(
            account_repo=ExchangeAccountRepository(session),
            order_repo=OrderRepository(session),
            account_service=account_service,
            bybit_futures_provider=bybit_futures_provider,
        ),
        user_repo=UserRepository(session),
    )


async def get_outcome_parity_service(
    session: AsyncSession = Depends(get_async_session),
) -> OutcomeParityService:
    """같은 DB 세션의 parity 조회 repository를 읽기 전용으로 조립한다."""
    return OutcomeParityService(
        session_repo=LiveSignalSessionRepository(session),
        parity_repo=ParityRepository(session),
        exchange_account_repo=ExchangeAccountRepository(session),
    )


async def get_alert_rule_service(
    session: AsyncSession = Depends(get_async_session),
) -> AlertRuleService:
    return AlertRuleService(
        repo=AlertRuleRepository(session),
        session_repo=LiveSignalSessionRepository(session),
    )


async def get_position_service(
    session: AsyncSession = Depends(get_async_session),
    account_service: ExchangeAccountService = Depends(get_exchange_account_service),
    bybit_futures_provider: BybitFuturesProvider = Depends(get_bybit_futures_provider),
) -> PositionService:
    return PositionService(
        session_repo=LiveSignalSessionRepository(session),
        account_repo=ExchangeAccountRepository(session),
        strategy_repo=StrategyRepository(session),
        account_service=account_service,
        bybit_futures_provider=bybit_futures_provider,
    )


async def get_close_service(
    session: AsyncSession = Depends(get_async_session),
    account_service: ExchangeAccountService = Depends(get_exchange_account_service),
    bybit_futures_provider: BybitFuturesProvider = Depends(get_bybit_futures_provider),
    order_service: OrderService = Depends(get_order_service),
) -> ClosePositionService:
    return ClosePositionService(
        session_repo=LiveSignalSessionRepository(session),
        account_repo=ExchangeAccountRepository(session),
        strategy_repo=StrategyRepository(session),
        account_service=account_service,
        bybit_futures_provider=bybit_futures_provider,
        order_service=order_service,
    )

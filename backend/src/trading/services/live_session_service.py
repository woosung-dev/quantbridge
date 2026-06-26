# trading service — LiveSignalSession 활성화/종료 + Pine 평가 진입 단독 책임 (Celery prefork-safe)

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.auth.repository import UserRepository
from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import StrategySettings, validate_strategy_settings
from src.trading.exceptions import (
    AccountModeNotAllowed,
    AccountNotFound,
    DemoAccountNotYetStable,
    InvalidStrategySettings,
    LiveSessionQuotaExceeded,
    SessionAlreadyActive,
    StrategySettingsRequired,
)
from src.trading.models import (
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
)
from src.trading.repositories.exchange_account_repository import (
    ExchangeAccountRepository,
)
from src.trading.repositories.live_signal_session_repository import (
    LiveSignalSessionRepository,
)
from src.trading.schemas import RegisterLiveSessionRequest

logger = logging.getLogger(__name__)

# Wave 0 W4 — 라이브 전환 전 요구 데모 안정화 기간(일). ponytail: 상수, 튜닝 필요 시 config 승격.
_MIN_DEMO_STABLE_DAYS = 7


class LiveSignalSessionService:
    """Sprint 26 — Pine signal evaluate session 등록/조회/종료.

    register: Bybit Demo 한정 + 사용자별 ≤ 5 active + Strategy.settings 의무.
    LESSON-019 commit-spy 의무 (Sprint 6 broken bug 패턴 재발 방어).

    BL-203 codex Fix #4 — Celery prefork-safe. module-level engine / provider /
    RedisLock / asyncio.Lock / create_async_engine() 캐시 금지. 모든 무거운 객체는
    함수 내부 lazy init.
    """

    def __init__(
        self,
        repo: LiveSignalSessionRepository,
        account_repo: ExchangeAccountRepository,
        strategy_repo: StrategyRepository,
        *,
        user_repo: UserRepository | None = None,
        max_active_per_user: int = 5,
    ) -> None:
        self._repo = repo
        self._account_repo = account_repo
        self._strategy_repo = strategy_repo
        self._user_repo = user_repo
        self._max_active_per_user = max_active_per_user

    async def register(self, user_id: UUID, req: RegisterLiveSessionRequest) -> LiveSignalSession:
        # 1. Strategy 조회 + ownership + StrategySettings.model_validate
        strategy = await self._strategy_repo.find_by_id_and_owner(req.strategy_id, user_id)
        if strategy is None:
            raise StrategyNotFoundError()

        if strategy.settings is None:
            raise StrategySettingsRequired(
                "Live Session 시작 prereq — PUT /api/v1/strategies/{id}/settings 로 "
                "leverage/margin_mode/position_size_pct 설정 후 재시도."
            )

        # codex G.0 P2 #4 — read path validate. malformed JSONB 방어.
        try:
            _settings: StrategySettings | None = validate_strategy_settings(strategy.settings)
        except ValidationError as e:
            raise InvalidStrategySettings(error=str(e)) from e

        # 2. ExchangeAccount 조회 + ownership + Bybit Demo 강제 (codex G.0 P2 #1)
        account = await self._account_repo.get_by_id(req.exchange_account_id)
        if account is None or account.user_id != user_id:
            raise AccountNotFound(req.exchange_account_id)

        # Wave 0 W4 — 라이브 경로 한정 demo-stability readiness 게이트.
        # 라이브는 어차피 AccountModeNotAllowed(stub)로 막히지만, 게이트를 앞에 둬
        # cutover(Wave 3) 시 데모 안정화 강제가 그대로 동작하도록 prep. demo 무영향.
        if account.mode == ExchangeMode.live:
            await self._enforce_demo_stability(user_id)

        # codex G.0 P2 #1 — ExchangeName.bybit (not 'bybit_futures' string).
        # Futures 여부는 settings.leverage is not None 으로 dispatch 분기 (Sprint 22 BL-091).
        if account.exchange != ExchangeName.bybit or account.mode != ExchangeMode.demo:
            raise AccountModeNotAllowed(
                exchange=account.exchange.value,
                mode=account.mode.value,
            )

        # 3. Quota lock (advisory + count_active + partial unique 이중 방어)
        await self._repo.acquire_quota_lock(user_id)
        current = await self._repo.count_active_by_user(user_id)
        if current >= self._max_active_per_user:
            raise LiveSessionQuotaExceeded(current=current, cap=self._max_active_per_user)

        # 4. INSERT — partial unique IntegrityError catch
        sess = LiveSignalSession(
            user_id=user_id,
            strategy_id=req.strategy_id,
            exchange_account_id=req.exchange_account_id,
            symbol=req.symbol,
            interval=LiveSignalInterval(req.interval),
        )
        try:
            saved = await self._repo.save(sess)
        except IntegrityError as e:
            raise SessionAlreadyActive(
                "Same (strategy_id, exchange_account_id, symbol) already active. "
                "Stop existing session first."
            ) from e

        # 5. LESSON-019 — Sprint 6 (webhook_secret) / 13 (OrderService) / 15-A
        # (ExchangeAccount) 와 동일 broken bug 4번째 재발 방어.
        await self._repo.commit()
        return saved

    async def _enforce_demo_stability(self, user_id: UUID) -> None:
        """라이브 전환 readiness — user.created_at 경과일 >= _MIN_DEMO_STABLE_DAYS 강제.

        조회 실패(None)는 검증 불가 → fail-closed(days_elapsed=0)로 거부.
        """
        created_at = (
            await self._user_repo.get_created_at(user_id) if self._user_repo else None
        )
        days_elapsed = (
            0 if created_at is None else (datetime.now(UTC) - created_at).days
        )
        if days_elapsed < _MIN_DEMO_STABLE_DAYS:
            raise DemoAccountNotYetStable(
                days_elapsed=days_elapsed, min_required=_MIN_DEMO_STABLE_DAYS
            )

    async def list_active(self, user_id: UUID) -> list[LiveSignalSession]:
        return list(await self._repo.list_active_by_user(user_id))

    async def deactivate(self, user_id: UUID, session_id: UUID) -> None:
        """ownership check + repo.deactivate + commit."""
        sess = await self._repo.get_by_id(session_id)
        if sess is None or sess.user_id != user_id:
            # ownership / 미존재 동일 404 (정보 누설 회피)
            raise StrategyNotFoundError()
        rowcount = await self._repo.deactivate(session_id, at=datetime.now(UTC))
        # rowcount==0 일 수 있음 (이미 deactivated). idempotent — error 안 함.
        if rowcount > 0:
            await self._repo.commit()  # LESSON-019

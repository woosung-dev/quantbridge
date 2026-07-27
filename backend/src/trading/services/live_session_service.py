# trading service — LiveSignalSession 활성화/종료 + Pine 평가 진입 단독 책임 (Celery prefork-safe)

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
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
    ProviderError,
    SessionAlreadyActive,
    SizingBaselineUnavailable,
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
from src.trading.services.balance_service import AccountBalanceService

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
        balance_service: AccountBalanceService,
        user_repo: UserRepository | None = None,
        max_active_per_user: int = 5,
    ) -> None:
        self._repo = repo
        self._account_repo = account_repo
        self._strategy_repo = strategy_repo
        self._balance_service = balance_service
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

        # 2.5 quota 사전 검사 (락 없음). 아래 잔고 조회는 CCXT 왕복이라 어차피 거부될 요청에
        # 태우면 낭비다. 권위 판정은 여전히 락 안의 재검사(:157) 이므로 레이스 안전성 무변경.
        pre_count = await self._repo.count_active_by_user(user_id)
        if pre_count >= self._max_active_per_user:
            raise LiveSessionQuotaExceeded(current=pre_count, cap=self._max_active_per_user)

        # 3. BL-479 자본 기준선 스냅샷 (세션당 1회).
        # free 는 기존 포지션 증거금을 제외하므로, 백테스트 init_cash 에 대응하는 total 을 쓴다.
        # 기준선 없이 통과하면 initial_capital=None 이 되어 compute_qty() 가 1.0 을 반환한다.
        # 1 BTC 명목이 나가는 그 실패가 BL-479 그 자체라 fail-closed 한다.
        # ProviderError(502) 로 새면 여기 적은 안내 문구가 가장 흔한 실패(네트워크/CCXT)에서
        # 도달 불가해지므로 같은 422 표면으로 모은다.
        # force_refresh — 이 값은 세션 내내 남는 사이징 기준선이라 15초 캐시를 물려받으면
        # 안 된다. 입금 직후 시작하면 입금 전 잔고로 세션 전체를 사이징하게 된다.
        try:
            balance = await self._balance_service.get_balance(
                user_id, account.id, force_refresh=True
            )
        except ProviderError as exc:
            raise SizingBaselineUnavailable(account_id=account.id, reason=str(exc)) from exc
        if not balance.supported or balance.total is None or balance.total <= Decimal("0"):
            raise SizingBaselineUnavailable(
                account_id=account.id,
                reason=balance.reason,
            )

        # 4. Quota lock (advisory + count_active + partial unique 이중 방어)
        # 잔고 조회를 락 앞에서 끝내 사용자별 등록 직렬화를 피한다.
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
            equity_baseline_usdt=balance.total,
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
        from src.tasks.websocket_task import run_bybit_public_ticker_stream

        try:
            run_bybit_public_ticker_stream.delay()
        except Exception as exc:
            # best-effort 즉시성 킥 — 실패해도 beat reconcile(5분)이 기동을 보증하므로
            # 세션 등록 성공을 500 으로 오염시키지 않는다.
            logger.warning("public_ticker_kick_failed err=%s", exc)
        return saved

    async def _enforce_demo_stability(self, user_id: UUID) -> None:
        """라이브 전환 readiness — user.created_at 경과일 >= _MIN_DEMO_STABLE_DAYS 강제.

        조회 실패(None)는 검증 불가 → fail-closed(days_elapsed=0)로 거부.
        """
        created_at = await self._user_repo.get_created_at(user_id) if self._user_repo else None
        days_elapsed = 0 if created_at is None else (datetime.now(UTC) - created_at).days
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
            from src.tasks.live_signal import sweep_conditional_entries_task

            try:
                sweep_conditional_entries_task.apply_async(expires=240)
            except Exception:
                logger.exception("conditional_entry_sweep_enqueue_failed")

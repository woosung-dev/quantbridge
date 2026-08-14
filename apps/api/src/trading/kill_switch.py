"""Kill Switch evaluators + service (spec S2.2).

각 evaluator는 독립적으로 테스트 가능. KillSwitchService가 DI로 주입받아 순회.

Sprint 12 Phase A: 첫 gated 전이 시 Slack alert 발송 (codex G0 #1 결정 — Service
layer hook, Evaluator 안 X). best-effort fire-and-forget. 자세한 정책은
``src/common/alert.py`` 모듈 docstring 참조.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import and_, func, select

from src.common.alert import send_critical_alert, track_pending_alert
from src.common.metrics import qb_kill_switch_triggered_total
from src.core.config import Settings, get_settings
from src.trading.exceptions import KillSwitchActive
from src.trading.models import (
    ExchangeAccount,
    KillSwitchEvent,
    KillSwitchTriggerType,
    Order,
    OrderState,
)
from src.trading.realtime_publisher import publish_realtime
from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
from src.trading.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    strategy_id: UUID
    account_id: UUID
    now: datetime


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    gated: bool
    trigger_type: Literal["cumulative_loss", "daily_loss", "api_error"] | None = None
    trigger_value: Decimal | None = None
    threshold: Decimal | None = None


class KillSwitchEvaluator(Protocol):
    async def evaluate(self, ctx: EvaluationContext) -> EvaluationResult: ...


class BalanceProvider(Protocol):
    """account별 USDT 잔고를 비동기로 조회. 동적 capital_base 바인딩용.

    Protocol로 선언하여 kill_switch → trading.service (ExchangeAccountService)
    순환 import 회피. None 반환 시 caller는 config fallback 사용.
    """

    async def fetch_balance_usdt(self, account_id: UUID) -> Decimal | None: ...


class CumulativeLossEvaluator:
    """MDD % = |누적 손실| / capital_base x 100. Strategy 단위.

    capital_base 우선순위:
    1. balance_provider로 조회한 실제 계좌 USDT 잔고 (>0)
    2. balance_provider가 None/실패 시 생성자 주입 capital_base (config fallback)

    Sprint 8+ (2026-04-20): ExchangeAccount.fetch_balance() 동적 바인딩 완료.
    BalanceProvider Protocol로 경계를 두어 trading.service와 순환 의존성 방지.
    """

    def __init__(
        self,
        repo: OrderRepository,
        *,
        threshold_percent: Decimal,
        capital_base: Decimal,
        balance_provider: BalanceProvider | None = None,
    ) -> None:
        self._repo = repo
        self._threshold = threshold_percent
        self._capital = capital_base
        self._balance_provider = balance_provider

    async def evaluate(self, ctx: EvaluationContext) -> EvaluationResult:
        # Strategy의 filled 주문 realized_pnl 합
        # ★[BL-726] 판정 (2026-08-14) — **`state == filled` 필터가 옳다.** 원장에
        #   `rejected` + `reduce_only=true` + `realized_pnl` 채움 46건 / **+55.32 USDT** 가
        #   있어 「값이 채워졌다(=청산으로 봤다)」와 「rejected(=발주 실패)」가 모순으로
        #   보이지만, 코드 대조하면 모순이 아니다:
        #     ⑴ `Order.realized_pnl` 은 **생성 시점**에 쓰인다 — `order_service.py:393,427` 이
        #        `state=OrderState.pending` 인 `Order(...)` 에 `realized_pnl=req.realized_pnl`
        #        을 싣는다. 생산자는 둘이고 **둘 다 추정치**다: 라이브 시그널 경로가
        #        `live_signal.py:4406`(MP-1) 의 `realized_pnl=event.realized_pnl`
        #        (= `LiveSignalEvent.realized_pnl`, `models.py:651` — pine_v2 시뮬 청산손익),
        #        웹훅 경로가 `router.py:161` 의 `realized_pnl=signal.realized_pnl`(TV alert 필드).
        #        ★**어느 쪽이든 결론이 같다** — 둘 다 체결 전 추정치다. 46건의 생산자를
        #        굳이 가르려면 `idempotency_key` 의 `live:` 접두로는 **부족하다**(웹훅도
        #        호출자가 준 `Idempotency-Key` 를 그대로 저장한다 — `router.py:104,171`).
        #        정본 판별 축은 `LiveSignalEvent.order_id` 조인이다(`models.py:674`).
        #     ⑵ 거래소 확정치를 쓰는 경로는 `backfill_exchange_realized_pnl` 과
        #        `resync_exchange_realized_pnl`(`order_repository.py:828`) **둘**이고,
        #        **둘 다** `.where(state == filled)` 를 요구하므로 `rejected` 행에는 못 들어간다.
        #   ⇒ 그 46건은 **체결된 적 없는 주문에 남은 시뮬 추정치**다. SUM 에서 빼는 게 맞고,
        #      부호가 + 라 넣으면 게이트가 손실을 과소평가한다. 거래소 응답이 그 사실을
        #      증언한다 — `error_message` 가 `retCode 110017 "current position is zero"` 30건 ·
        #      `"reduce-only order has same side"` 15건 · `retCode 10005` 1건이고
        #      `exchange_order_id` 는 46건 전부 NULL 이다.
        #      ★**「거래소에 도달조차 못 했다」는 틀린 표현이다**(2026-08-14 codex 적대 리뷰).
        #      `110017`·`10005` 는 **거래소가 반환한 retCode** 이므로 요청은 거래소까지 갔고
        #      거절당했다. 정확히는 **「주문 ID 가 발급되지 않았고 체결되지 않았다」**이다.
        #   ★확정/추정의 정본 축은 `realized_pnl_synced_at IS NOT NULL` 이다(`router.py` 의
        #     `"confirmed" if o.realized_pnl_synced_at is not None else "estimated"`). 그 축을
        #     여기 필터로 **추가하지 않는다** — 아직 백필 안 된 filled 주문의 추정 손익까지
        #     SUM 에서 빠져 게이트가 일시적으로 느슨해진다. 지금 필터가 더 안전한 쪽이다.
        stmt = select(func.coalesce(func.sum(Order.realized_pnl), 0)).where(
            and_(
                Order.strategy_id == ctx.strategy_id,  # type: ignore[arg-type]
                Order.state == OrderState.filled,  # type: ignore[arg-type]
            )
        )
        raw = (await self._repo.session.execute(stmt)).scalar_one()
        total_pnl = Decimal(str(raw))  # Decimal-first (Sprint 4 D8 교훈)

        if total_pnl >= Decimal("0"):
            return EvaluationResult(gated=False)

        # Sprint 8+ 동적 capital_base: balance_provider 주입 시 실제 잔고 우선.
        # None/0 이하는 config fallback (계좌 이관 중, API 실패 등 edge case 방어).
        # Sprint 28 Slice 4 (BL-004) — ADR-006 결의: KillSwitch trigger 시점 매번 호출
        # (Option A — accuracy 최대, latency +200ms 수용. Beta path A1 capital safety
        # 우선). provider 예외는 swallow + log + config fallback (resilience).
        capital = self._capital
        if self._balance_provider is not None:
            try:
                dynamic = await self._balance_provider.fetch_balance_usdt(ctx.account_id)
            except Exception as exc:
                logger.warning(
                    "balance_provider_failed account_id=%s err=%s — config fallback",
                    ctx.account_id,
                    exc,
                )
                dynamic = None
            if dynamic is not None and dynamic > Decimal("0"):
                capital = dynamic

        loss_percent = (abs(total_pnl) / capital * Decimal("100")).quantize(Decimal("0.01"))
        if loss_percent > self._threshold:
            return EvaluationResult(
                gated=True,
                trigger_type="cumulative_loss",
                trigger_value=loss_percent,
                threshold=self._threshold,
            )
        return EvaluationResult(gated=False)


class DailyLossEvaluator:
    """일일 손실 $ = UTC 당일 realized PnL 합. ExchangeAccount 단위."""

    def __init__(self, repo: OrderRepository, *, threshold_usd: Decimal) -> None:
        self._repo = repo
        self._threshold = threshold_usd

    async def evaluate(self, ctx: EvaluationContext) -> EvaluationResult:
        day_start = ctx.now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # ★[BL-726] `state == filled` 필터 판정 근거는 `CumulativeLossEvaluator.evaluate`
        #   주석에 있다 — 같은 판정이 두 SUM 에 함께 적용된다.
        stmt = select(func.coalesce(func.sum(Order.realized_pnl), 0)).where(
            and_(
                Order.exchange_account_id == ctx.account_id,  # type: ignore[arg-type]
                Order.state == OrderState.filled,  # type: ignore[arg-type]
                Order.filled_at >= day_start,  # type: ignore[arg-type,operator]
                Order.filled_at < day_end,  # type: ignore[arg-type,operator]
            )
        )
        daily: Decimal = Decimal(str((await self._repo.session.execute(stmt)).scalar_one()))

        if daily >= Decimal("0"):
            return EvaluationResult(gated=False)

        if abs(daily) > self._threshold:
            return EvaluationResult(
                gated=True,
                trigger_type="daily_loss",
                trigger_value=daily,
                threshold=self._threshold,
            )
        return EvaluationResult(gated=False)


class KillSwitchService:
    """Evaluator 순회 + 위반 시 KillSwitchEvent 기록 + 예외 raise.

    OrderService.execute() 진입부에서 ensure_not_gated 호출.

    Sprint 12 Phase A: 첫 gated 전이 시 Slack alert 발송 (best-effort).
    기존 unresolved 이벤트가 있는 경우(=재진입)는 alert 발송 X (이미 발송됨).
    """

    def __init__(
        self,
        evaluators: Sequence[KillSwitchEvaluator],
        events_repo: KillSwitchEventRepository,
        settings: Settings | None = None,
    ) -> None:
        self._evaluators = evaluators
        self._events_repo = events_repo
        # None → alert 발송 시점에 lru_cache get_settings() 로 lazy resolve.
        # 명시 주입은 test 또는 lifespan-owned singleton (Sprint 13+).
        self._settings = settings

    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        # 1. 기존 unresolved 이벤트 있으면 즉시 raise (재평가 스킵)
        existing = await self._events_repo.get_active(
            strategy_id=strategy_id, account_id=account_id
        )
        if existing is not None:
            raise KillSwitchActive(
                f"Active kill switch: {existing.trigger_type.value} (event_id={existing.id})"
            )

        # 2. Evaluator 순회 — 첫 위반에서 이벤트 기록 + raise
        ctx = EvaluationContext(strategy_id, account_id, datetime.now(UTC))
        for ev in self._evaluators:
            result = await ev.evaluate(ctx)
            if not result.gated:
                continue

            # Correction 3: assert → RuntimeError (T12 review I1)
            if (
                result.trigger_type is None
                or result.trigger_value is None
                or result.threshold is None
            ):
                raise RuntimeError(
                    "KillSwitchEvaluator returned gated=True with missing trigger fields"
                )

            # trigger_type별 strategy/account scope 매칭 (spec S2.2 + CHECK constraint)
            event = KillSwitchEvent(
                trigger_type=KillSwitchTriggerType(result.trigger_type),
                strategy_id=(strategy_id if result.trigger_type == "cumulative_loss" else None),
                exchange_account_id=(
                    account_id if result.trigger_type in ("daily_loss", "api_error") else None
                ),
                trigger_value=result.trigger_value,
                threshold=result.threshold,
            )
            # Correction 1: create() → save() (Sprint 6 convention)
            created = await self._events_repo.save(event)
            # ASYNC-1: 신규 breach 이벤트를 즉시 commit — 이후 KillSwitchActive raise 가
            # 호출자(OrderService)의 begin_nested SAVEPOINT 를 rollback 시켜도 audit row
            # 가 유실되지 않는다. ensure_not_gated 는 OrderService 의 order INSERT
            # savepoint *밖*에서 호출되므로 (order_service E9 restructure) 여기 commit 은
            # pending event 만 영속화 + alert/dedup 계약 보존 (alert storm 방지).
            await self._events_repo.commit()
            account = None
            with contextlib.suppress(Exception):
                account = await self._events_repo.session.get(ExchangeAccount, account_id)
            if account is not None:
                await publish_realtime(
                    str(account.user_id),
                    "kill_switch",
                    {"event_id": str(created.id), "trigger_type": result.trigger_type},
                )

            # Sprint 9 Phase D: 신규 발동만 카운트 (기존 unresolved 재히트는 제외).
            qb_kill_switch_triggered_total.labels(trigger_type=result.trigger_type).inc()

            # Sprint 12 Phase A: 첫 gated 전이 → Slack alert (fire-and-forget).
            # Sprint 19 BL-081: track_pending_alert() helper — set add + gauge
            # inc + idempotent done_callback (gauge 동기화). 기존 패턴
            # `_PENDING_ALERTS.add + discard` 의 cross-task semantic 명시화.
            task = asyncio.create_task(self._send_alert_safely(result, created))
            track_pending_alert(task)

            raise KillSwitchActive(
                f"New kill switch: {result.trigger_type} "
                f"(value={result.trigger_value}, threshold={result.threshold}, "
                f"event_id={created.id})"
            )

    async def _send_alert_safely(self, result: EvaluationResult, event: KillSwitchEvent) -> None:
        """Slack alert 발송. 실패는 swallow + log (raise 차단 금지)."""
        try:
            settings = self._settings or get_settings()
            title = f"Kill Switch — {result.trigger_type}"
            message = f"value={result.trigger_value}, threshold={result.threshold}"
            context = {
                "event_id": str(event.id),
                "strategy_id": (str(event.strategy_id) if event.strategy_id else "—"),
                "account_id": (
                    str(event.exchange_account_id) if event.exchange_account_id else "—"
                ),
                "trigger_type": str(result.trigger_type),
            }
            await send_critical_alert(settings, title, message, context)
        except Exception as exc:
            logger.warning("ks_alert_failed err=%s", exc)

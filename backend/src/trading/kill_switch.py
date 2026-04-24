"""Kill Switch evaluators + service (spec S2.2).

각 evaluator는 독립적으로 테스트 가능. KillSwitchService가 DI로 주입받아 순회.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import and_, func, select

from src.common.metrics import qb_kill_switch_triggered_total
from src.trading.exceptions import KillSwitchActive
from src.trading.models import (
    KillSwitchEvent,
    KillSwitchTriggerType,
    Order,
    OrderState,
)
from src.trading.repository import KillSwitchEventRepository, OrderRepository


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
        capital = self._capital
        if self._balance_provider is not None:
            dynamic = await self._balance_provider.fetch_balance_usdt(ctx.account_id)
            if dynamic is not None and dynamic > Decimal("0"):
                capital = dynamic

        loss_percent = (abs(total_pnl) / capital * Decimal("100")).quantize(
            Decimal("0.01")
        )
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

        stmt = select(func.coalesce(func.sum(Order.realized_pnl), 0)).where(
            and_(
                Order.exchange_account_id == ctx.account_id,  # type: ignore[arg-type]
                Order.state == OrderState.filled,  # type: ignore[arg-type]
                Order.filled_at >= day_start,  # type: ignore[arg-type,operator]
                Order.filled_at < day_end,  # type: ignore[arg-type,operator]
            )
        )
        daily: Decimal = Decimal(
            str((await self._repo.session.execute(stmt)).scalar_one())
        )

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
    """

    def __init__(
        self,
        evaluators: Sequence[KillSwitchEvaluator],
        events_repo: KillSwitchEventRepository,
    ) -> None:
        self._evaluators = evaluators
        self._events_repo = events_repo

    async def ensure_not_gated(
        self, strategy_id: UUID, account_id: UUID
    ) -> None:
        # 1. 기존 unresolved 이벤트 있으면 즉시 raise (재평가 스킵)
        existing = await self._events_repo.get_active(
            strategy_id=strategy_id, account_id=account_id
        )
        if existing is not None:
            raise KillSwitchActive(
                f"Active kill switch: {existing.trigger_type.value} "
                f"(event_id={existing.id})"
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
                strategy_id=(
                    strategy_id if result.trigger_type == "cumulative_loss" else None
                ),
                exchange_account_id=(
                    account_id
                    if result.trigger_type in ("daily_loss", "api_error")
                    else None
                ),
                trigger_value=result.trigger_value,
                threshold=result.threshold,
            )
            # Correction 1: create() → save() (Sprint 6 convention)
            created = await self._events_repo.save(event)

            # Sprint 9 Phase D: 신규 발동만 카운트 (기존 unresolved 재히트는 제외).
            qb_kill_switch_triggered_total.labels(
                trigger_type=result.trigger_type
            ).inc()

            raise KillSwitchActive(
                f"New kill switch: {result.trigger_type} "
                f"(value={result.trigger_value}, threshold={result.threshold}, "
                f"event_id={created.id})"
            )

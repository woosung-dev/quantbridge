"""거래소가 돌파 후 거절한 조건부 진입을 시장가로 복구하는 Celery 작업.

거래소의 110092/110093 거절은 해당 조건부 진입이 거래소 기준으로 이미 발화했다는
증거다. 엔진 시뮬레이션과 거래소를 다시 정렬하기 위해, 계획 시점 시장가 전환과 같은
안전장치를 거쳐 `condmkt` 복구 발주를 요청한다. 같은 idempotency key의 기존 요청에
합류할 수 있으므로 새 원장 행이나 실행 예약이 항상 생기지는 않는다.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from celery import shared_task
from pydantic import ValidationError

from src.common.metrics import _BYBIT_RETCODE_PATTERN, qb_live_conditional_guard_total
from src.common.metrics_multiproc import _count_safely
from src.core.config import settings
from src.strategy.schemas import validate_strategy_settings
from src.tasks._worker_engine import create_worker_engine_and_sm
from src.trading.models import OrderSide, OrderState, OrderType
from src.trading.providers import BybitFuturesProvider
from src.trading.services.order_service import OrderService

logger = logging.getLogger(__name__)

_BREACH_RETCODES = frozenset({"110092", "110093"})
_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


@shared_task(name="live_signal.recover_breached_entry", max_retries=0)  # type: ignore[untyped-decorator]
def conditional_entry_recovery_task(order_id: str) -> dict[str, str]:
    """거절된 조건부 진입 한 건을, 여전히 돌파 상태일 때만 시장가로 복구한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_recover_breached_entry(order_id))


async def _async_recover_breached_entry(order_id: str) -> dict[str, str]:
    """복구 결과를 반환한다.

    `recovery_placed`는 거래소 시장가 수락이 아니다. 복구 발주를 요청했으며, 신규
    원장 등재일 수도 있고 같은 idempotency key의 기존 요청에 합류한 캐시 응답일 수도 있다.
    """
    try:
        parsed_order_id = UUID(order_id)
    except (TypeError, ValueError):
        return {"order_id": str(order_id), "outcome": "not_applicable"}

    from src.auth.repository import UserRepository
    from src.strategy.repository import StrategyRepository
    from src.trading.dependencies import _CeleryOrderDispatcher, _StrategySessionsAdapter
    from src.trading.encryption import EncryptionService
    from src.trading.exceptions import ProviderError
    from src.trading.kill_switch import (
        CumulativeLossEvaluator,
        DailyLossEvaluator,
        KillSwitchEvaluator,
        KillSwitchService,
    )
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.account_service import ExchangeAccountService
    from src.trading.services.conditional_entry_planner import (
        build_market_converted_entry_key,
        parse_live_entry_key,
    )

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            order_repo = OrderRepository(session)
            order = await order_repo.get_by_id(parsed_order_id)
            if order is None or order.state != OrderState.rejected:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            ret_code_match = _BYBIT_RETCODE_PATTERN.search(order.error_message or "")
            if ret_code_match is None or ret_code_match.group(1) not in _BREACH_RETCODES:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            parsed_key = parse_live_entry_key(order.idempotency_key)
            if parsed_key is None or parsed_key.kind != "cond" or parsed_key.bar_epoch is None:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            trigger_price = order.trigger_price
            quantity = order.quantity
            trigger_direction = order.trigger_direction
            side = getattr(order.side, "value", order.side)
            expected_side = "buy" if trigger_direction == 1 else "sell"
            if (
                not isinstance(trigger_price, Decimal)
                or not trigger_price.is_finite()
                or not isinstance(quantity, Decimal)
                or not quantity.is_finite()
                or quantity <= Decimal("0")
                or trigger_direction not in (1, 2)
                or side != expected_side
                or order.reduce_only
            ):
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            session_repo = LiveSignalSessionRepository(session)
            live_session = await session_repo.get_by_id(parsed_key.session_id)
            if (
                live_session is None
                or not live_session.is_active
                or order.strategy_id != live_session.strategy_id
                or order.exchange_account_id != live_session.exchange_account_id
            ):
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            strategy = await StrategyRepository(session).find_by_id_and_owner(
                live_session.strategy_id, live_session.user_id
            )
            if strategy is None:
                return {"order_id": str(order_id), "outcome": "not_applicable"}
            try:
                strategy_settings = validate_strategy_settings(strategy.settings)
            except ValidationError:
                logger.warning(
                    "conditional_entry_recovery_invalid_settings",
                    extra={"order_id": str(order.id), "session_id": str(live_session.id)},
                )
                return {"order_id": str(order_id), "outcome": "not_applicable"}
            if strategy_settings is None:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            interval_seconds = _INTERVAL_SECONDS.get(str(live_session.interval))
            if interval_seconds is None:
                _count_safely(qb_live_conditional_guard_total, outcome="recovery_suppressed")
                logger.warning(
                    "conditional_entry_recovery_suppressed",
                    extra={
                        "order_id": str(order.id),
                        "session_id": str(live_session.id),
                        "reason": "unknown_interval",
                        "interval": str(live_session.interval),
                    },
                )
                return {"order_id": str(order_id), "outcome": "recovery_suppressed"}

            try:
                bar_time = datetime.fromtimestamp(parsed_key.bar_epoch, tz=UTC)
            except (OSError, OverflowError, ValueError):
                return {"order_id": str(order_id), "outcome": "not_applicable"}
            since = bar_time - timedelta(seconds=interval_seconds * 2)
            if await order_repo.has_recent_market_converted_entry(
                exchange_account_id=live_session.exchange_account_id,
                strategy_id=live_session.strategy_id,
                session_id=live_session.id,
                since=since,
            ):
                _count_safely(qb_live_conditional_guard_total, outcome="recovery_suppressed")
                logger.warning(
                    "conditional_entry_recovery_suppressed",
                    extra={
                        "order_id": str(order.id),
                        "session_id": str(live_session.id),
                        "reason": "recent_market_conversion",
                        "since": since.isoformat(),
                    },
                )
                return {"order_id": str(order_id), "outcome": "recovery_suppressed"}

            age = datetime.now(UTC) - order.created_at
            if age >= timedelta(seconds=interval_seconds):
                age_seconds = age.total_seconds()
                _count_safely(qb_live_conditional_guard_total, outcome="recovery_expired")
                logger.warning(
                    "conditional_entry_recovery_expired",
                    extra={
                        "order_id": str(order.id),
                        "session_id": str(live_session.id),
                        "age_seconds": age_seconds,
                        "interval_seconds": interval_seconds,
                    },
                )
                return {"order_id": str(order_id), "outcome": "recovery_expired"}

            account_repo = ExchangeAccountRepository(session)
            account = await account_repo.get_by_id(live_session.exchange_account_id)
            if account is None or account.user_id != live_session.user_id:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            bybit_provider = BybitFuturesProvider()
            exchange_service = ExchangeAccountService(
                repo=account_repo,
                crypto=EncryptionService(settings.trading_encryption_keys),
                bybit_futures_provider=bybit_provider,
            )
            try:
                reference_price = await bybit_provider.fetch_last_price(
                    await exchange_service.get_credentials_for_order(account.id),
                    live_session.symbol,
                )
            except ProviderError:
                logger.warning(
                    "conditional_entry_recovery_reference_unavailable",
                    exc_info=True,
                    extra={"order_id": str(order.id), "session_id": str(live_session.id)},
                )
                reference_price = None

            if (
                reference_price is None
                or not isinstance(reference_price, Decimal)
                or not reference_price.is_finite()
                or reference_price <= Decimal("0")
            ):
                _count_safely(qb_live_conditional_guard_total, outcome="reference_unavailable")
                logger.warning(
                    "conditional_entry_recovery_reference_unavailable",
                    extra={"order_id": str(order.id), "session_id": str(live_session.id)},
                )
                return {"order_id": str(order_id), "outcome": "reference_unavailable"}

            # 주문 행의 1=RISE=long=buy, 2=FALL=short=sell 매핑은 계획기의
            # `pending.direction` 기반 술어와 정상 행에서 동등하다.
            still_breached = (trigger_direction == 1 and trigger_price <= reference_price) or (
                trigger_direction == 2 and trigger_price >= reference_price
            )
            if not still_breached:
                _count_safely(qb_live_conditional_guard_total, outcome="recovery_reverted")
                logger.warning(
                    "conditional_entry_recovery_reverted",
                    extra={
                        "order_id": str(order.id),
                        "session_id": str(live_session.id),
                        "trigger_price": str(trigger_price),
                        "reference_price": str(reference_price),
                    },
                )
                return {"order_id": str(order_id), "outcome": "recovery_reverted"}

            max_breach_pct = (
                Decimal(str(strategy_settings.max_trigger_breach_pct))
                if strategy_settings.max_trigger_breach_pct is not None
                else None
            )
            breach_pct = abs(reference_price - trigger_price) / reference_price * Decimal("100")
            if max_breach_pct is not None and breach_pct > max_breach_pct:
                _count_safely(qb_live_conditional_guard_total, outcome="breach_capped")
                logger.warning(
                    "conditional_entry_recovery_breach_capped",
                    extra={
                        "order_id": str(order.id),
                        "session_id": str(live_session.id),
                        "trigger_price": str(trigger_price),
                        "reference_price": str(reference_price),
                        "breach_pct": str(breach_pct),
                        "max_breach_pct": str(max_breach_pct),
                    },
                )
                return {"order_id": str(order_id), "outcome": "breach_capped"}

            # 비활성화와 발주 사이 창을 줄인다. 원자적 보장을 주장하지 않으며, 기존
            # 계획 시점 전환과 같은 TOCTOU 성질은 OrderService 경로가 그대로 가진다.
            live_session = await session_repo.get_by_id(live_session.id)
            if live_session is None or not live_session.is_active:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            idempotency_key = build_market_converted_entry_key(
                live_session.id,
                parsed_key.trade_id,
                bar_time,
                trigger_price,
                quantity,
            )
            if idempotency_key is None:
                return {"order_id": str(order_id), "outcome": "not_applicable"}

            kse_repo = KillSwitchEventRepository(session)
            evaluators: list[KillSwitchEvaluator] = [
                CumulativeLossEvaluator(
                    order_repo,
                    threshold_percent=settings.kill_switch_cumulative_loss_percent,
                    capital_base=settings.kill_switch_capital_base_usd,
                    balance_provider=exchange_service,
                ),
                DailyLossEvaluator(
                    order_repo,
                    threshold_usd=settings.kill_switch_daily_loss_usd,
                ),
            ]
            order_service = OrderService(
                session=session,
                repo=order_repo,
                dispatcher=_CeleryOrderDispatcher(),
                kill_switch=KillSwitchService(evaluators=evaluators, events_repo=kse_repo),
                sessions_port=_StrategySessionsAdapter(
                    strategy_repo=StrategyRepository(session),
                    user_repo=UserRepository(session),
                ),
                exchange_service=exchange_service,
            )
            request = OrderRequest(
                strategy_id=live_session.strategy_id,
                exchange_account_id=live_session.exchange_account_id,
                symbol=live_session.symbol,
                side=OrderSide(side),
                type=OrderType.market,
                quantity=quantity,
                price=None,
                trigger_price=None,
                trigger_direction=None,
                trigger_by=None,
                reduce_only=False,
                leverage=strategy_settings.leverage,
                margin_mode=strategy_settings.margin_mode,
            )
            await order_service.execute(request, idempotency_key=idempotency_key, body_hash=None)

            _count_safely(qb_live_conditional_guard_total, outcome="recovery_placed")
            logger.info(
                "conditional_entry_recovery_placed",
                extra={
                    "order_id": str(order.id),
                    "session_id": str(live_session.id),
                    "recovery_idempotency_key": idempotency_key,
                },
            )
            return {"order_id": str(order_id), "outcome": "recovery_placed"}
    finally:
        await engine.dispose()

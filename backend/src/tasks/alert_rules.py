# 세션 귀속 실현 손실을 주기적으로 평가해 알림 규칙을 발화하는 Celery 태스크

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from celery import shared_task

from src.common.redis_client import get_redis_lock_pool
from src.core.config import settings
from src.tasks._worker_engine import create_worker_engine_and_sm
from src.tasks._worker_loop import run_in_worker_loop
from src.trading.alerting import send_rule_alert
from src.trading.encryption import EncryptionService
from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.alert_rule_repository import AlertRuleRepository
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.order_repository import OrderRepository, SessionScope
from src.trading.services.account_service import ExchangeAccountService

logger = logging.getLogger(__name__)
_ALERT_TTL_SECONDS = 3600


def _get_redis_lock_pool_for_alert() -> Any:
    """Redis pool 간접 함수로 태스크 테스트 monkeypatch 지점을 제공한다."""
    return get_redis_lock_pool()


async def _try_loss_alert_throttled(
    rule_id: str, *, title: str, message: str, channel: Any, context: dict[str, Any]
) -> bool:
    can_fire = bool(
        await _get_redis_lock_pool_for_alert().set(
            f"qb_rule_alert:{rule_id}".encode(), b"1", nx=True, ex=_ALERT_TTL_SECONDS
        )
    )
    if not can_fire:
        logger.info("alert_rule_throttled rule_id=%s", rule_id)
        return False
    await send_rule_alert(settings, channel=channel, title=title, message=message, context=context)
    return True


async def _async_evaluate_loss_rules() -> dict[str, int]:
    """prefork-safe worker 엔진 안에서 활성 손실 규칙만 평가한다."""
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            rule_repo = AlertRuleRepository(session)
            order_repo = OrderRepository(session)
            account_service = ExchangeAccountService(
                ExchangeAccountRepository(session),
                EncryptionService(settings.trading_encryption_keys),
                BybitFuturesProvider(),
            )
            evaluated = fired = 0
            for rule, live_session in await rule_repo.list_active_loss_rules_with_sessions():
                evaluated += 1
                # BL-444 — 예전에는 `live_signal_events` 조인이라 이벤트를 남기지 않는
                # 수동 청산·TV 웹훅 주문의 손실을 구조적으로 못 봤다.
                total_pnl = await order_repo.sum_filled_realized_pnl_for_session(
                    SessionScope.from_live_session(live_session)
                )
                if total_pnl >= Decimal("0"):
                    continue
                capital = settings.kill_switch_capital_base_usd
                try:
                    dynamic = await account_service.fetch_balance_usdt(
                        live_session.exchange_account_id
                    )
                except Exception:
                    logger.warning(
                        "alert_rule_balance_failed session_id=%s",
                        live_session.id,
                        exc_info=True,
                    )
                    dynamic = None
                if dynamic is not None and dynamic > Decimal("0"):
                    capital = dynamic
                loss_percent = (abs(total_pnl) / capital * Decimal("100")).quantize(Decimal("0.01"))
                threshold = rule.threshold_percent
                if threshold is None or loss_percent < threshold:
                    continue
                if await _try_loss_alert_throttled(
                    str(rule.id),
                    channel=rule.channel,
                    title="Live session loss limit reached",
                    message=(
                        f"Loss {loss_percent}% reached the {threshold}% threshold. "
                        "Scope: filled orders on this session's strategy, account and "
                        "symbol, filled within the session window."
                    ),
                    context={
                        "rule_id": str(rule.id)[:8],
                        "session_id": str(live_session.id)[:8],
                        "total_realized_pnl": str(total_pnl),
                        "loss_percent": str(loss_percent),
                        "threshold_percent": str(threshold),
                        "scope": (
                            "session strategy+account+symbol, filled_at within session window"
                        ),
                    },
                ):
                    fired += 1
            return {"evaluated": evaluated, "fired": fired}
    finally:
        await engine.dispose()


@shared_task(name="alert_rules.evaluate_loss")  # type: ignore[untyped-decorator]
def evaluate_loss_rules_task() -> dict[str, int]:
    return run_in_worker_loop(_async_evaluate_loss_rules())

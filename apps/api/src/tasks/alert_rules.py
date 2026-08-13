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


def _display_usd(value: Decimal) -> str:
    """알림 본문 **표시용** 반올림. 이 값을 산술로 되돌리지 않는다.

    `Order.realized_pnl` 은 `Numeric(18,8)` 이라 원시 문자열이 `-12.00000000` 로 온다.
    Slack 본문에서는 읽히지 않으므로 두 자리로 줄인다. 전정밀도가 필요한 쪽은
    `context` 가 따로 싣는다.
    """
    return f"{value.quantize(Decimal('0.01'))}"


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
                split = await order_repo.realized_pnl_split_for_session(
                    SessionScope.from_live_session(live_session)
                )
                # BL-458 — 게이트가 쓰는 값은 여전히 확정+추정 합계다. 추정을 빼면
                # 체결~스윕 도착 구간 손실이 통째로 사라져 fail-open 한다.
                total_pnl = split.total
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
                    title="라이브 세션 손실 한도 도달",
                    message=(
                        f"손실 {loss_percent}% 가 임계 {threshold}% 에 도달했습니다. "
                        # BL-458 — 이 숫자의 신뢰 등급을 본문에 드러낸다. 어휘는 FE
                        # 블로터(`ORDER_REALIZED_PNL_SOURCE_LABEL`)와 같은 두 단어다.
                        f"거래소 확정 {_display_usd(split.confirmed)} · "
                        f"추정 {_display_usd(split.estimated)} 을 합친 값입니다. "
                        "집계 범위는 이 세션의 전략·계정·심볼로 세션 창 안에서 체결된 "
                        "주문입니다."
                        + (
                            f" 손익이 아직 기록되지 않은 체결 {split.unrecorded_count}건은 "
                            "이 합계에 없어 실제 손실이 더 클 수 있습니다."
                            if split.unrecorded_count
                            else ""
                        )
                    ),
                    context={
                        # ★기존 6 키는 기계 판독용이라 byte-identical 로 보존한다.
                        "rule_id": str(rule.id)[:8],
                        "session_id": str(live_session.id)[:8],
                        "total_realized_pnl": str(total_pnl),
                        "loss_percent": str(loss_percent),
                        "threshold_percent": str(threshold),
                        "scope": (
                            "session strategy+account+symbol, filled_at within session window"
                        ),
                        # BL-458 신규 — 본문은 사람용, context 는 포렌식용이므로 여기는
                        # 표시 반올림 없이 전정밀도로 싣는다.
                        "confirmed_realized_pnl": str(split.confirmed),
                        "estimated_realized_pnl": str(split.estimated),
                        "confirmed_count": str(split.confirmed_count),
                        "estimated_count": str(split.estimated_count),
                        "unrecorded_count": str(split.unrecorded_count),
                    },
                ):
                    fired += 1
            return {"evaluated": evaluated, "fired": fired}
    finally:
        await engine.dispose()


@shared_task(name="alert_rules.evaluate_loss")  # type: ignore[untyped-decorator]
def evaluate_loss_rules_task() -> dict[str, int]:
    return run_in_worker_loop(_async_evaluate_loss_rules())

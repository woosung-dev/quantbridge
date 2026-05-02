"""Sprint 15 Phase A.3 — orphan_scanner Celery beat (BL-001 + BL-002).

scan_stuck_orders_task — 30분 이상 stuck 주문 자동 reconcile + alert.

Scope (codex G.0 P1 #3 반영):
- pending + created_at < cutoff               → execute_order_task.apply_async (dispatch 복구)
- submitted + submitted_at < cutoff + ex_id   → fetch_order_status_task.apply_async (terminal 확인)
- submitted + submitted_at < cutoff + null id → throttled alert 만 (수동 cleanup)

Alert dedupe: per-cycle Redis SET NX EX 30min — 동일 cycle 중복 발화 회피.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.common.alert import send_critical_alert
from src.common.redis_client import get_redis_lock_pool
from src.core.config import settings
from src.tasks.trading import execute_order_task, fetch_order_status_task
from src.trading.repository import OrderRepository

logger = logging.getLogger(__name__)


# Sprint 17 Phase A — Celery prefork worker 의 매 task 마다 asyncio.run() 으로
# 새 event loop 가 생기는데, asyncpg connection pool 은 생성 당시 loop 에 bind
# 되므로 module-level cached engine 은 두 번째 task 부터 InterfaceError("another
# operation is in progress") 로 silent fail. 따라서 funding.py / backtest.py 와
# 동일하게 매 호출마다 fresh engine + finally dispose.
def create_worker_engine_and_sm() -> (
    tuple[AsyncEngine, async_sessionmaker[AsyncSession]]
):
    """매 호출마다 새 engine + async_sessionmaker 튜플 반환.

    호출자는 engine 을 finally 에서 dispose 해야 한다. 테스트는 이 함수를
    monkeypatch 로 대체하여 공유 세션 + no-op engine 주입 가능.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


def _get_redis_lock_pool_for_alert() -> Any:
    """Redis pool indirection — test 가 monkeypatch 가능."""
    return get_redis_lock_pool()


_SCAN_STUCK_THRESHOLD_MINUTES = 30
_ALERT_THROTTLE_TTL_SECONDS = 1800  # 30분 — 다음 scan cycle (5분 beat) 6번 통과


async def _try_alert_throttled(
    cycle_key: str, message: str, context: dict[str, Any]
) -> bool:
    """SET NX EX 1800 — 동일 cycle_key 의 두 번째 alert 차단.

    cycle_key 는 "stuck:<order_id>" 등 — per-order dedupe.
    """
    pool = _get_redis_lock_pool_for_alert()
    redis_key = f"qb_scan_alert:{cycle_key}".encode()
    can_fire = bool(
        await pool.set(redis_key, b"1", nx=True, ex=_ALERT_THROTTLE_TTL_SECONDS)
    )
    if not can_fire:
        logger.info("scan_alert_throttled cycle_key=%s", cycle_key)
        return False

    await send_critical_alert(
        settings,
        title="Stuck orders detected",
        message=message,
        context=context,
    )
    return True


async def _async_scan_stuck_orders() -> dict[str, Any]:
    """Core scan logic. Sprint 17 Phase A: per-call engine + finally dispose."""
    cutoff = datetime.now(UTC) - timedelta(minutes=_SCAN_STUCK_THRESHOLD_MINUTES)

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = OrderRepository(session)
            stuck_pending = await repo.list_stuck_pending(cutoff)
            stuck_submitted = await repo.list_stuck_submitted(cutoff)
            stuck_interrupted = await repo.list_stuck_submission_interrupted(cutoff)

        # 1. pending — execute_order_task 재enqueue (dispatch 누락 복구).
        for order in stuck_pending:
            execute_order_task.apply_async(args=[str(order.id)], countdown=0)
            await _try_alert_throttled(
                cycle_key=f"pending:{order.id}",
                message=(
                    f"Pending order stuck > {_SCAN_STUCK_THRESHOLD_MINUTES}min "
                    "— re-dispatched"
                ),
                context={
                    "order_id": str(order.id)[:8],
                    "symbol": order.symbol,
                    "created_at": order.created_at.isoformat(),
                    "kind": "pending_stuck",
                },
            )

        # 2. submitted + ex_id — fetch_order_status_task 재enqueue (terminal evidence).
        for order in stuck_submitted:
            fetch_order_status_task.apply_async(
                args=[str(order.id)], countdown=0
            )
            # alert 는 fetch_order_status_task 가 attempt>=max 후 별도 발화.

        # 3. submitted + null ex_id — throttled alert 만 (manual cleanup).
        for order in stuck_interrupted:
            await _try_alert_throttled(
                cycle_key=f"interrupted:{order.id}",
                message=(
                    "Order stuck submitted with NULL exchange_order_id — "
                    "submission interrupted (worker crash or race). "
                    "Manual cleanup required."
                ),
                context={
                    "order_id": str(order.id)[:8],
                    "symbol": order.symbol,
                    "submitted_at": (
                        order.submitted_at.isoformat()
                        if order.submitted_at
                        else "unknown"
                    ),
                    "kind": "submission_interrupted",
                },
            )

        return {
            "pending": len(stuck_pending),
            "submitted": len(stuck_submitted),
            "interrupted": len(stuck_interrupted),
        }
    finally:
        await engine.dispose()


@shared_task(name="trading.scan_stuck_orders")  # type: ignore[untyped-decorator]
def scan_stuck_orders_task() -> dict[str, Any]:
    """Sprint 15 Phase A.3 — Celery beat 5분 schedule.

    Idempotency: state guard (각 enqueue 된 task 가 다시 state 확인) + Redis throttle.

    Sprint 18 BL-080 (Option C): asyncio.run() → run_in_worker_loop. 영속
    `_WORKER_LOOP` 재사용으로 asyncpg connection 의 transport waiter 가 stale
    loop 참조 안 함. (라이브 evidence: same child 의 2nd+ task 가 fail 하던
    회귀 차단)
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_scan_stuck_orders())

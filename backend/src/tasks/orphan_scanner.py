"""Sprint 15 Phase A.3 — orphan_scanner Celery beat (BL-001 + BL-002).

scan_stuck_orders_task — 30분 이상 stuck 주문 자동 reconcile + alert.

Scope (codex G.0 P1 #3 반영):
- pending + created_at < cutoff               → execute_order_task.apply_async (dispatch 복구)
- submitted + submitted_at < cutoff + ex_id   → fetch_order_status_task.apply_async (terminal 확인)
- submitted + submitted_at < cutoff + null id → throttled alert 만 (수동 cleanup)

Alert dedupe: per-cycle Redis SET NX EX 30min — 동일 cycle 중복 발화 회피.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.common.alert import send_critical_alert
from src.common.redis_client import get_redis_lock_pool
from src.core.config import settings
from src.tasks.trading import execute_order_task, fetch_order_status_task
from src.trading.repository import OrderRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker-local lazy session factory (mirrors src.tasks.trading pattern)
# ---------------------------------------------------------------------------
_worker_engine = None
_sessionmaker_cache: async_sessionmaker[AsyncSession] | None = None


def async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Worker-local async_sessionmaker. Lazy init per child process.

    Tests monkeypatch this at module level.
    """
    global _worker_engine, _sessionmaker_cache
    if _sessionmaker_cache is None:
        _worker_engine = create_async_engine(settings.database_url, echo=False)
        _sessionmaker_cache = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _sessionmaker_cache


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
    """Core scan logic. Sprint 16+ 에서 multi-instance 병렬 실행 시 lease 추가 검토."""
    cutoff = datetime.now(UTC) - timedelta(minutes=_SCAN_STUCK_THRESHOLD_MINUTES)

    sm = async_session_factory()
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
            message=f"Pending order stuck > {_SCAN_STUCK_THRESHOLD_MINUTES}min — re-dispatched",
            context={
                "order_id": str(order.id)[:8],
                "symbol": order.symbol,
                "created_at": order.created_at.isoformat(),
                "kind": "pending_stuck",
            },
        )

    # 2. submitted + ex_id — fetch_order_status_task 재enqueue (terminal evidence 확인).
    for order in stuck_submitted:
        fetch_order_status_task.apply_async(
            args=[str(order.id)], countdown=0
        )
        # alert 는 fetch_order_status_task 가 attempt>=max 후 별도 발화 (qb_watchdog_alert).
        # scan 시점엔 noise 줄이기 위해 alert 안 함.

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
                    order.submitted_at.isoformat() if order.submitted_at else "unknown"
                ),
                "kind": "submission_interrupted",
            },
        )

    return {
        "pending": len(stuck_pending),
        "submitted": len(stuck_submitted),
        "interrupted": len(stuck_interrupted),
    }


@shared_task(name="trading.scan_stuck_orders")  # type: ignore[untyped-decorator]
def scan_stuck_orders_task() -> dict[str, Any]:
    """Sprint 15 Phase A.3 — Celery beat 5분 schedule.

    Idempotency: state guard (각 enqueue 된 task 가 다시 state 확인) + Redis throttle.
    """
    return asyncio.run(_async_scan_stuck_orders())

"""WebSocket order event → DB transition + alert (Sprint 12 Phase C).

설계 (codex G0/G3 결정):
- orderLinkId 우선 lookup (UUID(orderLinkId) → Order.id). exchange_order_id fallback.
- REST/WS race buffer: 5s TTL, FIFO max 1000 entries (codex G3 #2 hard cap).
- terminal status 만 transition: New (skip — 보통 REST 가 이미 submitted),
  Filled / Cancelled / Rejected. PartiallyFilled 는 MVP skip (codex G3 #8).
- Rejected 시 Slack alert (Phase A send_critical_alert 재사용).
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.common.alert import send_critical_alert
from src.common.metrics import (
    qb_active_orders,
    qb_ws_orphan_buffer_size,
    qb_ws_orphan_event_total,
)
from src.core.config import Settings
from src.trading.models import OrderState
from src.trading.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


_ORPHAN_TTL_S = 5.0
_ORPHAN_MAX = 1000


# Bybit V5 orderStatus → local OrderState. PartiallyFilled / New 은 skip.
_BYBIT_TERMINAL_MAP: dict[str, OrderState] = {
    "Filled": OrderState.filled,
    "Cancelled": OrderState.cancelled,
    "Rejected": OrderState.rejected,
}


SessionFactory = Callable[[], Any]  # async context manager 반환


class StateHandler:
    """WebSocket order event 처리기.

    `session_factory` 는 ``AsyncSession`` 을 반환하는 async context manager.
    M2 Slim — Sprint 13+ 에서 multi-stream 시 lock 추가 검토.
    """

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        settings: Settings,
        alert_sender: Callable[..., Awaitable[bool]] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        # test injection — None 이면 Phase A send_critical_alert 사용
        self._alert_sender = alert_sender or send_critical_alert
        # orderLinkId / exchange_order_id → (payload, ts) FIFO
        self._orphan_buffer: OrderedDict[str, tuple[dict[str, Any], float]] = (
            OrderedDict()
        )

    async def handle_order_event(
        self, account_id: UUID, payload: dict[str, Any]
    ) -> None:
        order_link_id = payload.get("orderLinkId")
        exchange_order_id = payload.get("orderId")

        async with self._session_factory() as session:
            repo = OrderRepository(session)

            order = None
            # 우선순위 1: orderLinkId == str(Order.id) UUID
            if order_link_id:
                # orderLinkId 가 UUID 형식 아니면 (외부 등록 / legacy) skip
                with contextlib.suppress(ValueError):
                    order = await repo.get_by_id(UUID(order_link_id))
            # fallback: exchange_order_id
            if order is None and exchange_order_id:
                order = await self._get_by_exchange_order_id(
                    repo, exchange_order_id
                )

            if order is None:
                # REST 가 아직 Order row 생성 못 함 / exchange_order_id 미저장
                # → 5s buffer (codex G0-7)
                key = order_link_id or exchange_order_id or ""
                self._buffer_orphan(key, payload, account_id)
                return

            # terminal status 만 transition (codex G3 #10)
            new_state = _BYBIT_TERMINAL_MAP.get(payload.get("orderStatus", ""))
            if new_state is None:
                # New / PartiallyFilled / 기타 — MVP skip
                return

            # Sprint 16 BL-027 (codex G.0 P1 #1): commit-then-dec winner-only.
            # _apply_transition 은 rowcount 만 return — dec/alert 호출은 caller responsibility.
            # commit 성공 후에만 dec 발화 (commit 실패 시 DB rollback ↔ gauge 일관 보장).
            rowcount = await self._apply_transition(repo, order.id, new_state, payload)
            await session.commit()

            if rowcount == 1:
                if new_state in (
                    OrderState.filled,
                    OrderState.rejected,
                    OrderState.cancelled,
                ):
                    qb_active_orders.dec()

                if new_state == OrderState.rejected:
                    await self._alert_sender(
                        self._settings,
                        "Order Rejected (WS)",
                        f"{order.symbol} {order.side} {order.quantity}",
                        {
                            "order_id": str(order.id),
                            "account_id": str(account_id),
                            "reason": payload.get("rejectReason", "unknown"),
                        },
                    )

    async def replay_orphan(self, key: str, account_id: UUID) -> bool:
        """REST 응답 직후 호출 — buffer 에 있으면 재처리 + 제거. True if replayed."""
        entry = self._orphan_buffer.pop(key, None)
        qb_ws_orphan_buffer_size.set(len(self._orphan_buffer))
        if entry is None:
            return False
        payload, _ = entry
        await self.handle_order_event(account_id, payload)
        return True

    def _buffer_orphan(
        self, key: str, payload: dict[str, Any], account_id: UUID
    ) -> None:
        """5s TTL + FIFO max 1000 (codex G3 #2)."""
        # 새 entry 등록 (이미 있으면 갱신 + reorder)
        self._orphan_buffer[key] = (payload, time.time())
        self._orphan_buffer.move_to_end(key, last=True)

        # FIFO eviction
        while len(self._orphan_buffer) > _ORPHAN_MAX:
            self._orphan_buffer.popitem(last=False)

        # 5s TTL — 앞에서부터 stale 제거 (insertion order = 시간 순)
        cutoff = time.time() - _ORPHAN_TTL_S
        while self._orphan_buffer:
            first_key = next(iter(self._orphan_buffer))
            _, ts = self._orphan_buffer[first_key]
            if ts >= cutoff:
                break
            self._orphan_buffer.popitem(last=False)

        qb_ws_orphan_buffer_size.set(len(self._orphan_buffer))
        qb_ws_orphan_event_total.labels(account_id=str(account_id)).inc()
        logger.debug(
            "ws_orphan_buffered account=%s key=%s buffer_size=%d",
            account_id,
            key,
            len(self._orphan_buffer),
        )

    async def _apply_transition(
        self,
        repo: OrderRepository,
        order_id: UUID,
        new_state: OrderState,
        payload: dict[str, Any],
    ) -> int:
        """Sprint 16 BL-027: rowcount return — caller 가 commit 성공 후 winner-only dec/alert.

        codex G.0 P1 #1: 이전엔 dec() 가 commit 전 발화 → commit 실패/rollback 시
        DB 는 active 인데 gauge 만 감소 = drift. 패턴 통일 (`tasks/trading.py:458`):
        rows == 1 → commit 성공 → dec.
        """
        now = datetime.now(UTC)
        if new_state == OrderState.filled:
            avg = payload.get("avgPrice") or payload.get("average")
            from decimal import Decimal

            filled_price = Decimal(str(avg)) if avg else None
            return await repo.transition_to_filled(
                order_id,
                exchange_order_id=str(payload.get("orderId", "")),
                filled_price=filled_price,
                filled_at=now,
            )
        elif new_state == OrderState.rejected:
            reason = payload.get("rejectReason", "ws_rejected")
            return await repo.transition_to_rejected(
                order_id,
                error_message=f"ws_rejected: {reason}",
                failed_at=now,
            )
        elif new_state == OrderState.cancelled:
            return await repo.transition_to_cancelled(order_id, cancelled_at=now)
        return 0

    async def _get_by_exchange_order_id(
        self, repo: OrderRepository, exchange_order_id: str
    ) -> Any:
        """OrderRepository 가 이 메소드를 직접 제공하지 않으면 raw SQL 로."""
        from sqlalchemy import select

        from src.trading.models import Order

        stmt = select(Order).where(
            Order.exchange_order_id == exchange_order_id  # type: ignore[arg-type]
        )
        result = await repo.session.execute(stmt)
        return result.scalar_one_or_none()

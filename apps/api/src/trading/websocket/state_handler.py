"""WebSocket order event → DB transition + alert (Sprint 12 Phase C).

설계 (codex G0/G3 결정):
- orderLinkId 우선 lookup (UUID(orderLinkId) → Order.id). exchange_order_id fallback.
- terminal status 만 transition: New (skip — 보통 REST 가 이미 submitted),
  Filled / Cancelled / Rejected. PartiallyFilled 는 MVP skip (codex G3 #8).
- Rejected 시 Slack alert (Phase A send_critical_alert 재사용).

★**고아 이벤트(로컬 행이 없는 WS 이벤트)의 복구 경로는 reconciler 하나뿐이다** (BL-448).
원래는 REST/WS 경합용 5초 재생 버퍼(`_orphan_buffer` + `replay_orphan`)가 있었으나 **REST
승자 경로가 그것을 부른 적이 없다** — 테스트에서만 호출됐다. 그래서 버퍼는 재생 장치가 아니라
지연된 폐기장이었고(항목은 TTL 이나 FIFO 축출로만 빠져나갔다), 폐기 시점에 로그·메트릭이
전무해 **유실이 관측되지 않았다.** 버퍼를 되살리는 대신 걷어내고 폐기를 그 자리에서 계상한다.

복구는 `reconciliation.Reconciler` 가 맡는다 — reconnect/first-connect 직후
(`bybit_private_stream.py:263`) local `pending`/`submitted` 를 거래소 스냅샷과 대조해 종결
증거가 있으면 전이시킨다. 그래서 **우리가 발주한 주문**의 놓친 종결 이벤트는 회수된다.
반대로 로컬 행이 끝내 안 생기는 이벤트(외부 주문 등)는 reconciler 가 local→exchange 단방향이라
INSERT 하지 않으므로 회수되지 않는다 — 이건 의도한 것이고, 그 폐기를
`qb_ws_orphan_discarded_total` 이 센다.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.common.alert import send_critical_alert
from src.common.metrics import (
    qb_active_orders,
    qb_ws_orphan_discarded_total,
    qb_ws_orphan_event_total,
    record_partial_fill,
)
from src.common.metrics_multiproc import record_metric_safely
from src.core.config import Settings
from src.trading.models import OrderState
from src.trading.realtime_publisher import publish_realtime
from src.trading.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


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
        user_id: UUID | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        # test injection — None 이면 Phase A send_critical_alert 사용
        self._alert_sender = alert_sender or send_critical_alert
        self._user_id = user_id

    async def handle_order_event(self, account_id: UUID, payload: dict[str, Any]) -> None:
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
                order = await repo.get_by_exchange_order_id(exchange_order_id)

            if order is None:
                # 로컬 행이 없다 — 회수는 reconciler 몫이므로 여기선 폐기하고 계상한다.
                key = order_link_id or exchange_order_id or ""
                self._discard_orphan(key, payload, account_id)
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
                if self._user_id is not None:
                    await publish_realtime(
                        str(self._user_id),
                        "order_update",
                        {
                            "order_id": str(order.id),
                            "state": new_state.value,
                            "symbol": order.symbol,
                            "side": order.side.value,
                            "source": "ws",
                        },
                    )
                if new_state in (
                    OrderState.filled,
                    OrderState.rejected,
                    OrderState.cancelled,
                ):
                    record_metric_safely(qb_active_orders.dec)

                if new_state == OrderState.filled:
                    # STEP B — WS fill winner: trailing 의도 entry 면 place_trailing_stop enqueue.
                    #   동기/WS/watchdog winner-only 전이라 정확히 1회만 발화(구조적 dedup).
                    #   동기/watchdog 와 동일한 `_enqueue_trailing_if_intended` helper 재사용
                    #   (inline 복제 금지 — divergence 차단). lazy import 로 순환 의존 회피.
                    from decimal import Decimal

                    from src.tasks.trading import (
                        _enqueue_closed_pnl_refresh,
                        _enqueue_conditional_reversal_measure,
                        _enqueue_trailing_if_intended,
                    )

                    filled = payload.get("cumExecQty") or payload.get("filled")
                    filled_quantity = Decimal(str(filled)) if filled else None
                    if (
                        filled_quantity is not None
                        and filled_quantity.is_finite()
                        and filled_quantity < order.quantity
                    ):
                        record_partial_fill(source="ws", reduce_only=order.reduce_only)
                    _enqueue_trailing_if_intended(order)
                    _enqueue_closed_pnl_refresh(order)
                    _enqueue_conditional_reversal_measure(order)

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

    def _discard_orphan(self, key: str, payload: dict[str, Any], account_id: UUID) -> None:
        """로컬 행이 없는 WS 이벤트를 폐기하고 **폐기 축**으로 계상한다 (BL-448).

        ★도착 축(`qb_ws_orphan_event_total`)과 따로 세는 이유 — 도착 수만으로는 **무엇을
        잃었는지** 알 수 없다. 종결 상태(`Filled`/`Cancelled`/`Rejected`) 이벤트를 잃는 것은
        머니-패스 손실이고 reconciler 가 회수해야 할 대상인 반면, 비종결(`New` ·
        `PartiallyFilled` 등)은 로컬 행이 있었어도 어차피 skip 했을 무해한 값이다. 한 카운터로
        뭉치면 이 둘이 섞여 경보 문턱을 정할 수 없다.

        같은 이유로 종결 이벤트만 `warning` 으로 올린다. 종전 `logger.debug` 는 프로덕션
        로그 레벨에서 아무것도 안 남겼다 — 「폐기 시점에 로그·메트릭·알림 전무」의 실체다.
        """
        status = str(payload.get("orderStatus", "") or "")
        is_terminal = status in _BYBIT_TERMINAL_MAP
        reason = "terminal_event_lost" if is_terminal else "non_terminal_ignored"

        qb_ws_orphan_event_total.labels(account_id=str(account_id)).inc()
        qb_ws_orphan_discarded_total.labels(account_id=str(account_id), reason=reason).inc()

        log = logger.warning if is_terminal else logger.debug
        log(
            "ws_orphan_discarded account=%s key=%s status=%s reason=%s",
            account_id,
            key,
            status or "unknown",
            reason,
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
            filled = payload.get("cumExecQty") or payload.get("filled")
            from decimal import Decimal

            filled_price = Decimal(str(avg)) if avg else None
            filled_quantity = Decimal(str(filled)) if filled else None
            return await repo.transition_to_filled(
                order_id,
                exchange_order_id=str(payload.get("orderId", "")),
                filled_price=filled_price,
                filled_quantity=filled_quantity,
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

"""Reconciler — reconnect 직후 REST 스냅샷 diff (Sprint 12 Phase C).

설계 (codex G0/G3):
- reconnect (+ first connect, codex G3 #11) 직후 호출. debounce 30s 는
  ``BybitPrivateStream._maybe_reconcile`` 가 처리.
- ``fetch_open_orders`` + ``fetch_recent_orders`` (limit 50) 의 union 에서
  local pending/submitted order 매칭.
- **terminal evidence 만 state transition** (codex G3 #10) — exchange status
  가 ``Cancelled / Rejected / Filled`` 명시적이면 transition. 그 외 (open 에 없음
  + recent 에 없음) = state 유지 + Slack alert + ``qb_ws_reconcile_unknown_total``.

Sprint 13 이관:
- circuit breaker (auth fail 시 account 격리)
- Bybit 의 long-running disconnect 시 missed event 보정 (현재 30s window 만)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.alert import send_critical_alert
from src.common.metrics import qb_active_orders, qb_ws_reconcile_unknown_total
from src.core.config import Settings
from src.trading.models import Order, OrderState
from src.trading.repository import OrderRepository

logger = logging.getLogger(__name__)


# G4 revisit fix #11: CCXT unified status 와 Bybit raw status 둘 다 수용.
# - CCXT fetch_*_orders 는 status 를 "open"/"closed"/"canceled"/"rejected" 로 정규화.
# - Bybit V5 raw API 는 "New"/"Filled"/"Cancelled"/"Rejected".
# 양쪽 모두 매핑하여 운영 reconciler 가 dead code 안 되도록.
_TERMINAL_STATUSES = frozenset(
    {"Cancelled", "Rejected", "Filled", "closed", "canceled", "rejected"}
)
_STATUS_MAP: dict[str, OrderState] = {
    # Bybit V5 raw
    "Filled": OrderState.filled,
    "Cancelled": OrderState.cancelled,
    "Rejected": OrderState.rejected,
    # CCXT unified
    "closed": OrderState.filled,
    "canceled": OrderState.cancelled,
    "rejected": OrderState.rejected,
}


class ReconcileFetcher(Protocol):
    """Reconciler 가 사용하는 REST snapshot 소스.

    실제 운영에서는 ``BybitDemoProvider`` 와 별도로 구현 (또는 확장).
    test 에서는 mock dict 반환.
    """

    async def fetch_open_orders(self, account_id: UUID) -> list[dict[str, Any]]: ...

    async def fetch_recent_orders(
        self, account_id: UUID, *, limit: int = 50
    ) -> list[dict[str, Any]]: ...


class Reconciler:
    """reconnect 직후 호출. local active order 와 exchange snapshot diff 적용."""

    def __init__(
        self,
        *,
        session_factory: Any,  # async context manager → AsyncSession
        fetcher: ReconcileFetcher,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._fetcher = fetcher
        self._settings = settings

    async def run(self, *, account_id: UUID) -> None:
        async with self._session_factory() as session:
            local_active = await self._list_local_active(session, account_id)
            if not local_active:
                return

            exch_open = await self._fetcher.fetch_open_orders(account_id)
            exch_recent = await self._fetcher.fetch_recent_orders(
                account_id, limit=50
            )
            all_exch = exch_open + exch_recent

            # Sprint 16 BL-027 (codex G.0 P1 #1): commit-then-dec winner-only.
            # _apply_transition 가 rowcount return → 누적 후 commit 성공 시점에 dec 발화.
            winners: list[OrderState] = []
            for local in local_active:
                exch = self._find_match(all_exch, str(local.id))
                if exch is None:
                    # codex G3 #10: terminal evidence 없이 cancel 금지.
                    # state 유지 + alert + metric.
                    await self._handle_unknown(local, account_id)
                    continue

                status = exch.get("status", "")
                if status in _TERMINAL_STATUSES:
                    new_state = _STATUS_MAP[status]
                    if new_state != local.state:
                        rowcount = await self._apply_transition(
                            session, local, new_state, exch
                        )
                        if rowcount == 1:
                            winners.append(new_state)
                # else: 명시 status 없으면 state 유지

            await session.commit()

            # Sprint 16 BL-027: commit 성공 후 winner-only dec — 이전엔 dec 누락 (drift).
            for new_state in winners:
                if new_state in (
                    OrderState.filled,
                    OrderState.rejected,
                    OrderState.cancelled,
                ):
                    qb_active_orders.dec()

    async def _list_local_active(
        self, session: AsyncSession, account_id: UUID
    ) -> list[Order]:
        """pending / submitted state 의 local order 조회."""
        stmt = select(Order).where(
            Order.exchange_account_id == account_id,  # type: ignore[arg-type]
            Order.state.in_(  # type: ignore[attr-defined]
                [OrderState.pending, OrderState.submitted]
            ),
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _find_match(
        self, exch_orders: list[dict[str, Any]], local_id: str
    ) -> dict[str, Any] | None:
        """clientOrderId 또는 orderLinkId 가 local_id 와 일치."""
        for o in exch_orders:
            client_id = (
                o.get("clientOrderId")
                or o.get("orderLinkId")
                or o.get("clOrdId")
            )
            if client_id == local_id:
                return o
        return None

    async def _handle_unknown(self, local: Order, account_id: UUID) -> None:
        """exchange 에 없는 local active order — state 유지 + alert + metric."""
        qb_ws_reconcile_unknown_total.labels(
            account_id=str(account_id)
        ).inc()
        # 1h 이상 stale 인 경우 더 강한 warning
        age_hours = (
            datetime.now(UTC) - local.created_at
        ).total_seconds() / 3600
        stale_marker = " (stale >1h)" if age_hours > 1 else ""
        try:
            await send_critical_alert(
                self._settings,
                f"Order Reconcile Unknown{stale_marker}",
                f"Order {local.id} not found in exchange open/recent. "
                f"Local state {local.state} unchanged. Manual verification needed.",
                {
                    "order_id": str(local.id),
                    "account_id": str(account_id),
                    "local_state": local.state,
                    "age_hours": f"{age_hours:.1f}",
                    "symbol": local.symbol,
                },
            )
        except Exception as exc:
            logger.warning("reconcile_alert_failed err=%s", exc)

    async def _apply_transition(
        self,
        session: AsyncSession,
        local: Order,
        new_state: OrderState,
        exch: dict[str, Any],
    ) -> int:
        """Sprint 16 BL-027: rowcount return — caller (run) 가 commit 성공 후 winner-only dec.

        codex G.0 P1 #1: 이전엔 dec() 자체 누락 → reconcile transition 시 gauge 감소
        안 됨 = drift. caller layer 에서 commit-then-dec 패턴으로 통일.
        """
        repo = OrderRepository(session)
        now = datetime.now(UTC)
        rowcount = 0
        if new_state == OrderState.filled:
            from decimal import Decimal

            avg = exch.get("average") or exch.get("avgPrice")
            filled_price = Decimal(str(avg)) if avg else None
            rowcount = await repo.transition_to_filled(
                local.id,
                exchange_order_id=str(exch.get("id", local.exchange_order_id or "")),
                filled_price=filled_price,
                filled_at=now,
            )
        elif new_state == OrderState.cancelled:
            rowcount = await repo.transition_to_cancelled(local.id, cancelled_at=now)
        elif new_state == OrderState.rejected:
            reason = exch.get("info", {}).get("rejectReason", "reconcile_rejected")
            rowcount = await repo.transition_to_rejected(
                local.id, error_message=str(reason), failed_at=now
            )
        logger.info(
            "ws_reconcile_transition order=%s old=%s new=%s rowcount=%d",
            local.id,
            local.state,
            new_state,
            rowcount,
        )
        return rowcount

    # NOTE: Sprint 13 follow-up — 1h stale + cancelled-by-evidence 별도 정책 추가 가능.
    _STALE_HOURS = timedelta(hours=1)

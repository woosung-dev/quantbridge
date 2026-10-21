"""라이브 세션의 사용자 범위 읽기 응답을 조립하는 서비스."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, cast
from uuid import UUID

from src.trading.equity_calculator import (
    RealizedPnlSource,
    label_curve_provenance,
    recompute_equity_curve,
)
from src.trading.repositories.code_checkpoint_repository import CodeCheckpointRepository
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository, SessionScope
from src.trading.schemas import (
    CodeExecutionSummary,
    LiveSignalEventListResponse,
    LiveSignalEventResponse,
    LiveSignalStateResponse,
)


class LiveSessionQueryService:
    def __init__(
        self,
        session_repo: LiveSignalSessionRepository,
        order_repo: OrderRepository,
        event_repo: LiveSignalEventRepository,
        checkpoint_repo: CodeCheckpointRepository,
        risk_repo: CodeRiskRepository,
    ) -> None:
        self._session_repo = session_repo
        self._order_repo = order_repo
        self._event_repo = event_repo
        self._checkpoint_repo = checkpoint_repo
        self._risk_repo = risk_repo

    async def get_state_for_user(
        self, session_id: UUID, user_id: UUID
    ) -> LiveSignalStateResponse | None:
        sess = await self._session_repo.get_by_id_for_user(session_id, user_id)
        if sess is None:
            return None
        is_code = (sess.execution_snapshot or {}).get("source_policy") == "code_v1"
        state = None if is_code else await self._session_repo.get_state(session_id)
        code_summary = None
        pnl_complete = None
        unpriced_exit_orders = 0
        evaluated = state is not None
        updated_at = state.updated_at if state is not None else None
        if is_code:
            checkpoint = await self._checkpoint_repo.latest(session_id)
            risk = await self._risk_repo.get(session_id)
            evaluated = checkpoint is not None and not checkpoint.is_warmup
            timestamps = [
                t
                for t in (
                    checkpoint.created_at if checkpoint else None,
                    risk.updated_at if risk else None,
                )
                if t is not None
            ]
            updated_at = max(timestamps) if timestamps else None
            code_summary = CodeExecutionSummary(
                version_id=sess.strategy_version_id,
                checkpoint_status=cast(
                    Literal["warmup", "prepared", "delivered", "blocked"], checkpoint.status
                )
                if checkpoint
                else None,
                last_bar_time=checkpoint.bar_time if checkpoint else None,
                last_intent=checkpoint.intent if checkpoint else None,
                risk_generation=risk.generation if risk else None,
                direction=risk.direction if risk else None,
                position_quantity=risk.position_quantity if risk else None,
                entry_vwap=risk.entry_vwap if risk else None,
                fixed_r=risk.fixed_r if risk else None,
                protection_pending=bool(
                    risk
                    and risk.position_quantity > 0
                    and risk.protection_desired
                    and risk.protection_desired.get("token") != risk.protection_applied.get("token")
                ),
                trailing_active=risk.trailing_active if risk else False,
                new_entries_blocked=risk.new_entries_blocked if risk else False,
                failure_reason=risk.failure_reason if risk else None,
                pending_reversal=risk.pending_reversal if risk else None,
                unsettled_exit_quantity=risk.unsettled_exit_quantity if risk else Decimal(0),
            )
            unpriced_exit_orders = await self._order_repo.count_unpriced_exit_fills_for_session(
                SessionScope.from_live_session(sess)
            )
            pnl_complete = code_summary.unsettled_exit_quantity == 0 and unpriced_exit_orders == 0
        if state is None and not is_code:
            return LiveSignalStateResponse(
                session_id=session_id,
                evaluated=False,
                schema_version=0,
                last_strategy_state_report={},
                total_closed_trades=0,
                total_realized_pnl=Decimal("0"),
                equity_curve=[],
                updated_at=None,
            )

        order_repo = self._order_repo
        # BL-445 — 예전에는 `(strategy, account)` 튜플만 넘겨서 같은 튜플 위의 비활성
        # 세션들이 하나의 커브를 공유했다. 세션 창·심볼까지 담은 스코프를 넘긴다.
        filled_orders = await order_repo.list_filled_realized_for_session(
            SessionScope.from_live_session(sess)
        )
        # BL-458 — 출처를 커브·소계와 **한 리스트에서** 파생한다. 두 번째 comprehension 에
        # 같은 2절 필터를 복제하면 누가 한쪽만 고치는 날 라벨이 조용히 어긋난다.
        rows: list[tuple[int, Decimal, RealizedPnlSource]] = [
            (
                int(o.filled_at.timestamp() * 1000),
                Decimal(str(o.realized_pnl)),
                "confirmed" if o.realized_pnl_synced_at is not None else "estimated",
            )
            for o in filled_orders
            if o.filled_at is not None and o.realized_pnl is not None
        ]
        closed_pnls = [(timestamp_ms, pnl) for timestamp_ms, pnl, _ in rows]
        real_total_realized_pnl = sum(
            (pnl for _, pnl in closed_pnls), Decimal("0")
        )  # Decimal-first 합산 (Sprint 4 D8)
        real_equity_curve = label_curve_provenance(
            recompute_equity_curve(closed_pnls), [source for _, _, source in rows]
        )
        # 소계도 Decimal-first. `total` 은 기존 계산을 그대로 두므로 항등식
        # `confirmed + estimated == total` 이 대입이 아니라 **산술로** 성립한다.
        confirmed_pnl = sum((pnl for _, pnl, source in rows if source == "confirmed"), Decimal("0"))
        estimated_pnl = sum((pnl for _, pnl, source in rows if source == "estimated"), Decimal("0"))

        return LiveSignalStateResponse(
            session_id=session_id,
            evaluated=evaluated,
            code_execution=code_summary,
            pnl_complete=pnl_complete,
            pnl_scope="known_order_subtotal" if is_code else None,
            unpriced_exit_orders=unpriced_exit_orders,
            schema_version=state.schema_version if state else 0,
            last_strategy_state_report=state.last_strategy_state_report if state else {},
            total_closed_trades=len(closed_pnls),
            total_realized_pnl=real_total_realized_pnl,
            confirmed_realized_pnl=confirmed_pnl,
            estimated_realized_pnl=estimated_pnl,
            confirmed_closed_trades=sum(1 for _, _, s in rows if s == "confirmed"),
            estimated_closed_trades=sum(1 for _, _, s in rows if s == "estimated"),
            equity_curve=[dict(p) for p in real_equity_curve],  # TypedDict → dict 호환 cast
            updated_at=updated_at,
        )

    async def list_events_for_user(
        self, session_id: UUID, user_id: UUID, *, limit: int
    ) -> LiveSignalEventListResponse | None:
        sess = await self._session_repo.get_by_id_for_user(session_id, user_id)
        if sess is None:
            return None
        event_rows = await self._event_repo.list_by_session_with_order_state(
            session_id, limit=limit
        )
        return LiveSignalEventListResponse(
            items=[
                LiveSignalEventResponse.model_validate(event).model_copy(
                    update={"order_state": order_state}
                )
                for event, order_state in event_rows
            ]
        )

"""라이브 세션의 사용자 범위 읽기 응답을 조립하는 서비스."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from src.trading.equity_calculator import (
    RealizedPnlSource,
    label_curve_provenance,
    recompute_equity_curve,
)
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository, SessionScope
from src.trading.schemas import (
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
    ) -> None:
        self._session_repo = session_repo
        self._order_repo = order_repo
        self._event_repo = event_repo

    async def get_state_for_user(
        self, session_id: UUID, user_id: UUID
    ) -> LiveSignalStateResponse | None:
        sess = await self._session_repo.get_by_id_for_user(session_id, user_id)
        if sess is None:
            return None
        state = await self._session_repo.get_state(session_id)
        if state is None:
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
            session_id=state.session_id,
            schema_version=state.schema_version,
            last_strategy_state_report=state.last_strategy_state_report,
            total_closed_trades=len(closed_pnls),
            total_realized_pnl=real_total_realized_pnl,
            confirmed_realized_pnl=confirmed_pnl,
            estimated_realized_pnl=estimated_pnl,
            confirmed_closed_trades=sum(1 for _, _, s in rows if s == "confirmed"),
            estimated_closed_trades=sum(1 for _, _, s in rows if s == "estimated"),
            equity_curve=[dict(p) for p in real_equity_curve],  # TypedDict → dict 호환 cast
            updated_at=state.updated_at,
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

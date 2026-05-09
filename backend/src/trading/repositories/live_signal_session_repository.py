# trading repository — LiveSignalSession (전략 활성 세션) 영속화 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import LiveSignalSession, LiveSignalState

# interval → seconds CASE expression (list_active_due 에서 SQL-side 필터)
_INTERVAL_SECONDS_CASE = (
    "CASE interval "
    "WHEN '1m'  THEN INTERVAL '60 seconds' "
    "WHEN '5m'  THEN INTERVAL '300 seconds' "
    "WHEN '15m' THEN INTERVAL '900 seconds' "
    "WHEN '1h'  THEN INTERVAL '3600 seconds' "
    "END"
)


class LiveSignalSessionRepository:
    """Sprint 26 — Pine signal evaluate session CRUD + race-safe bar claim.

    LESSON-019 commit-spy 의무 — Service mutation 메서드 마다 await commit().
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, sess: LiveSignalSession) -> LiveSignalSession:
        self.session.add(sess)
        await self.session.flush()
        return sess

    async def get_by_id(self, session_id: UUID) -> LiveSignalSession | None:
        result = await self.session.execute(
            select(LiveSignalSession).where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_active_by_user(self, user_id: UUID) -> Sequence[LiveSignalSession]:
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712  # type: ignore[arg-type]
            .order_by(LiveSignalSession.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def count_active_by_user(self, user_id: UUID) -> int:
        """Sprint 26 quota check — 사용자별 active session ≤ 5."""
        result = await self.session.execute(
            select(func.count(LiveSignalSession.id))  # type: ignore[arg-type]
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712  # type: ignore[arg-type]
        )
        return int(result.scalar_one() or 0)

    async def acquire_quota_lock(self, user_id: UUID) -> None:
        """PG advisory xact lock — quota race 방어 (codex G.0 P3 #3 + plan §3 A.4).

        partial unique index 와 함께 이중 방어 (Sprint 11 advisory pattern).
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"live_session_quota:{user_id}"},
        )

    async def list_active_due(self, now: datetime) -> Sequence[LiveSignalSession]:
        """interval 별 due session list — codex G.0 P2 #3 패턴 + plan §3 A.4.

        is_active=true AND (last_evaluated_bar_time IS NULL
                            OR last_evaluated_bar_time + interval_seconds <= now).
        Beat task evaluate_live_signals 가 1분 fire 마다 호출.
        """
        # _INTERVAL_SECONDS_CASE 는 module-level constant (사용자 input X) — S608 false positive
        stmt = text(
            "SELECT * FROM trading.live_signal_sessions "  # noqa: S608
            "WHERE is_active = true "
            "AND (last_evaluated_bar_time IS NULL "
            f"     OR last_evaluated_bar_time + ({_INTERVAL_SECONDS_CASE}) <= :now) "
            "ORDER BY id"
        )
        result = await self.session.execute(stmt, {"now": now})
        rows = result.mappings().all()
        return [LiveSignalSession(**dict(row)) for row in rows]

    async def try_claim_bar(
        self, session_id: UUID, bar_time: datetime, claim_token: UUID
    ) -> bool:
        """codex G.0 P2 #3 — winner-only bar claim.

        UPDATE WHERE id=session_id AND is_active=true AND
        (last_evaluated_bar_time IS NULL OR last_evaluated_bar_time < bar_time).
        rowcount==1 → True (claim 성공). 0 → False (다른 task 가 이미 claim 또는 같은 bar).

        race-safe: 두 worker 가 같은 bar_time 으로 동시 호출해도 1번만 True 반환.
        """
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .where(
                or_(
                    LiveSignalSession.last_evaluated_bar_time.is_(None),  # type: ignore[union-attr]
                    LiveSignalSession.last_evaluated_bar_time < bar_time,  # type: ignore[operator,arg-type]
                )
            )
            .values(
                last_evaluated_bar_time=bar_time,
                bar_claim_token=claim_token,
                updated_at=datetime.now(UTC),
            )
        )
        return (result.rowcount or 0) == 1  # type: ignore[attr-defined]

    async def deactivate(self, session_id: UUID, *, at: datetime) -> int:
        """is_active=False + deactivated_at. Service 가 commit 책임."""
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .values(is_active=False, deactivated_at=at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def get_state(self, session_id: UUID) -> LiveSignalState | None:
        result = await self.session.execute(
            select(LiveSignalState).where(LiveSignalState.session_id == session_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def upsert_state(
        self,
        *,
        session_id: UUID,
        last_strategy_state_report: dict[str, object],
        last_open_trades_snapshot: dict[str, object],
        total_closed_trades: int,
        total_realized_pnl: Decimal,
        equity_curve: list[dict[str, object]] | None = None,
    ) -> LiveSignalState:
        """INSERT ON CONFLICT DO UPDATE on session_id (1:1 with sessions).

        Service 가 같은 트랜잭션에서 events INSERT + state upsert + commit (codex G.0 P1 #3).

        Sprint 28 Slice 3 (BL-140b): equity_curve 신규 (optional, default None = 갱신 안함).
        Task 가 calculator 로 새 datapoint append 후 전체 array 전달.
        """
        existing = await self.get_state(session_id)
        if existing is None:
            state = LiveSignalState(
                session_id=session_id,
                last_strategy_state_report=last_strategy_state_report,
                last_open_trades_snapshot=last_open_trades_snapshot,
                total_closed_trades=total_closed_trades,
                total_realized_pnl=total_realized_pnl,
                equity_curve=equity_curve if equity_curve is not None else [],
                updated_at=datetime.now(UTC),
            )
            self.session.add(state)
            await self.session.flush()
            return state
        existing.last_strategy_state_report = last_strategy_state_report
        existing.last_open_trades_snapshot = last_open_trades_snapshot
        existing.total_closed_trades = total_closed_trades
        existing.total_realized_pnl = total_realized_pnl
        if equity_curve is not None:
            existing.equity_curve = equity_curve
        existing.updated_at = datetime.now(UTC)
        await self.session.flush()
        return existing

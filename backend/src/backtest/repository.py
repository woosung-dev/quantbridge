"""BacktestRepository — AsyncSession 유일 보유, DB 접근 전담."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade


class BacktestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 트랜잭션 제어 ---

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # --- CRUD ---

    async def create(self, bt: Backtest) -> Backtest:
        self.session.add(bt)
        await self.session.flush()
        return bt

    async def get_by_id(
        self, backtest_id: UUID, *, user_id: UUID | None = None
    ) -> Backtest | None:
        stmt = select(Backtest).where(Backtest.id == backtest_id)  # type: ignore[arg-type]
        if user_id is not None:
            stmt = stmt.where(Backtest.user_id == user_id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, *, limit: int, offset: int
    ) -> tuple[Sequence[Backtest], int]:
        total_stmt = select(func.count()).select_from(Backtest).where(
            Backtest.user_id == user_id  # type: ignore[arg-type]
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(Backtest)
            .where(Backtest.user_id == user_id)  # type: ignore[arg-type]
            .order_by(Backtest.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def delete(self, backtest_id: UUID) -> int:
        result = await self.session.execute(
            delete(Backtest).where(Backtest.id == backtest_id)  # type: ignore[arg-type]
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    # --- 조건부 상태 전이 (3-guard cancel logic §5.1) ---

    async def transition_to_running(
        self, backtest_id: UUID, *, started_at: datetime
    ) -> int:
        """queued → running. 조건부 UPDATE. Returns affected rows."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == BacktestStatus.QUEUED)  # type: ignore[arg-type]
            .values(status=BacktestStatus.RUNNING, started_at=started_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def complete(
        self,
        backtest_id: UUID,
        *,
        metrics: dict[str, Any],
        equity_curve: list[Any],
        where_status: BacktestStatus = BacktestStatus.RUNNING,
    ) -> int:
        """Running → completed. 조건부. Returns affected rows."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == where_status)  # type: ignore[arg-type]
            .values(
                status=BacktestStatus.COMPLETED,
                metrics=metrics,
                equity_curve=equity_curve,
                completed_at=datetime.now(UTC),
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def fail(
        self,
        backtest_id: UUID,
        *,
        error: str,
        where_status: BacktestStatus = BacktestStatus.RUNNING,
    ) -> int:
        """Running → failed. 조건부."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == where_status)  # type: ignore[arg-type]
            .values(
                status=BacktestStatus.FAILED,
                error=error[:2000],  # defensive truncation
                completed_at=datetime.now(UTC),
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def request_cancel(self, backtest_id: UUID) -> int:
        """queued/running → cancelling. 조건부."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(
                Backtest.status.in_(  # type: ignore[attr-defined]
                    [BacktestStatus.QUEUED, BacktestStatus.RUNNING]
                )
            )
            .values(status=BacktestStatus.CANCELLING)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def finalize_cancelled(
        self, backtest_id: UUID, *, completed_at: datetime
    ) -> int:
        """cancelling → cancelled. 조건부. Worker guards에서 호출."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == BacktestStatus.CANCELLING)  # type: ignore[arg-type]
            .values(status=BacktestStatus.CANCELLED, completed_at=completed_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    # --- Trades ---

    async def insert_trades_bulk(self, trades: list[BacktestTrade]) -> None:
        """Bulk insert. Transaction 내에서 호출 (service가 commit)."""
        self.session.add_all(trades)
        await self.session.flush()

    async def list_trades(
        self, backtest_id: UUID, *, limit: int, offset: int
    ) -> tuple[Sequence[BacktestTrade], int]:
        total_stmt = select(func.count()).select_from(BacktestTrade).where(
            BacktestTrade.backtest_id == backtest_id  # type: ignore[arg-type]
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)  # type: ignore[arg-type]
            .order_by(BacktestTrade.trade_index.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    # --- Idempotency (Sprint 9-6) ---

    async def get_by_idempotency_key(self, key: str) -> Backtest | None:
        result = await self.session.execute(
            select(Backtest).where(Backtest.idempotency_key == key)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def acquire_idempotency_lock(self, key: str) -> None:
        """pg_advisory_xact_lock — 트랜잭션 종료 시 자동 해제."""
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": key},
        )

    # --- Cross-domain query (§4.8 Strategy delete 선조회) ---

    async def exists_for_strategy(self, strategy_id: UUID) -> bool:
        stmt = select(func.count()).select_from(Backtest).where(
            Backtest.strategy_id == strategy_id  # type: ignore[arg-type]
        )
        count = (await self.session.execute(stmt)).scalar_one()
        return count > 0

    # --- Stale reclaim (§8.3) ---

    async def reclaim_stale(
        self, *, threshold_seconds: int, now: datetime
    ) -> tuple[int, int]:
        """running/cancelling 중 stale → terminal.

        Running: started_at + threshold < now → failed.
        Cancelling: started_at 있으면 그 기준, 없으면 (QUEUED→CANCELLING 케이스)
                    created_at + threshold < now 기준으로 reclaim → cancelled.
                    후자 없으면 worker가 pickup 못 한 queued-cancel이 영영 stuck.

        Returns (reclaimed_running, reclaimed_cancelling).
        """
        cutoff = now - timedelta(seconds=threshold_seconds)

        running_result = await self.session.execute(
            update(Backtest)
            .where(Backtest.status == BacktestStatus.RUNNING)  # type: ignore[arg-type]
            .where(Backtest.started_at < cutoff)  # type: ignore[arg-type,operator]
            .values(
                status=BacktestStatus.FAILED,
                error="Stale running — reclaimed by worker startup",
                completed_at=now,
            )
        )
        cancelling_result = await self.session.execute(
            update(Backtest)
            .where(Backtest.status == BacktestStatus.CANCELLING)  # type: ignore[arg-type]
            .where(
                or_(
                    Backtest.started_at < cutoff,  # type: ignore[arg-type,operator]
                    and_(
                        Backtest.started_at.is_(None),  # type: ignore[union-attr]
                        Backtest.created_at < cutoff,  # type: ignore[arg-type]
                    ),
                )
            )
            .values(
                status=BacktestStatus.CANCELLED,
                completed_at=now,
            )
        )
        return (
            running_result.rowcount or 0,  # type: ignore[attr-defined]
            cancelling_result.rowcount or 0,  # type: ignore[attr-defined]
        )

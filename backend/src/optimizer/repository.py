"""OptimizationRepository — AsyncSession 유일 보유, DB 접근 전담.

stress_test/repository.py pattern 1:1 mirror. Sprint 18 BL-080 + LESSON-019 commit 의무.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.optimizer.models import OptimizationRun, OptimizationStatus


class OptimizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 트랜잭션 ---

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # --- CRUD ---

    async def create(self, run: OptimizationRun) -> OptimizationRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_by_id(
        self, run_id: UUID, *, user_id: UUID | None = None
    ) -> OptimizationRun | None:
        stmt = select(OptimizationRun).where(OptimizationRun.id == run_id)  # type: ignore[arg-type]
        if user_id is not None:
            stmt = stmt.where(OptimizationRun.user_id == user_id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        backtest_id: UUID | None = None,
    ) -> tuple[Sequence[OptimizationRun], int]:
        base = select(OptimizationRun).where(OptimizationRun.user_id == user_id)  # type: ignore[arg-type]
        total_base = select(func.count()).select_from(OptimizationRun).where(
            OptimizationRun.user_id == user_id  # type: ignore[arg-type]
        )
        if backtest_id is not None:
            base = base.where(OptimizationRun.backtest_id == backtest_id)  # type: ignore[arg-type]
            total_base = total_base.where(
                OptimizationRun.backtest_id == backtest_id  # type: ignore[arg-type]
            )

        total = (await self.session.execute(total_base)).scalar_one()
        stmt = (
            base.order_by(OptimizationRun.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    # --- 상태 전이 ---

    async def transition_to_running(
        self, run_id: UUID, *, started_at: datetime
    ) -> int:
        """queued → running. UPDATE rows=0 → silent skip (stress_test pattern mirror)."""
        result = await self.session.execute(
            update(OptimizationRun)
            .where(OptimizationRun.id == run_id)  # type: ignore[arg-type]
            .where(OptimizationRun.status == OptimizationStatus.QUEUED)  # type: ignore[arg-type]
            .values(status=OptimizationStatus.RUNNING, started_at=started_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def complete(
        self,
        run_id: UUID,
        *,
        result: dict[str, Any],
    ) -> int:
        """running → completed."""
        update_result = await self.session.execute(
            update(OptimizationRun)
            .where(OptimizationRun.id == run_id)  # type: ignore[arg-type]
            .where(OptimizationRun.status == OptimizationStatus.RUNNING)  # type: ignore[arg-type]
            .values(
                status=OptimizationStatus.COMPLETED,
                result=result,
                completed_at=datetime.now(UTC),
            )
        )
        return update_result.rowcount or 0  # type: ignore[attr-defined]

    async def fail(
        self,
        run_id: UUID,
        *,
        error_message: str,
        where_status: OptimizationStatus | None = None,
    ) -> int:
        """→ failed. error_message 는 service 가 truncate_error_message 적용 후 호출 (BL-230)."""
        stmt = (
            update(OptimizationRun)
            .where(OptimizationRun.id == run_id)  # type: ignore[arg-type]
            .values(
                status=OptimizationStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.now(UTC),
            )
        )
        if where_status is not None:
            stmt = stmt.where(OptimizationRun.status == where_status)  # type: ignore[arg-type]
        else:
            stmt = stmt.where(
                OptimizationRun.status.in_(  # type: ignore[attr-defined]
                    [OptimizationStatus.QUEUED, OptimizationStatus.RUNNING]
                )
            )
        update_result = await self.session.execute(stmt)
        return update_result.rowcount or 0  # type: ignore[attr-defined]

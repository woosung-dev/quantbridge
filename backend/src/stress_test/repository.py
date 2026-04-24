"""StressTestRepository — AsyncSession 유일 보유, DB 접근 전담."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.stress_test.models import StressTest, StressTestStatus


class StressTestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 트랜잭션 ---

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # --- CRUD ---

    async def create(self, st: StressTest) -> StressTest:
        self.session.add(st)
        await self.session.flush()
        return st

    async def get_by_id(
        self, stress_test_id: UUID, *, user_id: UUID | None = None
    ) -> StressTest | None:
        stmt = select(StressTest).where(StressTest.id == stress_test_id)  # type: ignore[arg-type]
        if user_id is not None:
            stmt = stmt.where(StressTest.user_id == user_id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        backtest_id: UUID | None = None,
    ) -> tuple[Sequence[StressTest], int]:
        base = select(StressTest).where(StressTest.user_id == user_id)  # type: ignore[arg-type]
        total_base = select(func.count()).select_from(StressTest).where(
            StressTest.user_id == user_id  # type: ignore[arg-type]
        )
        if backtest_id is not None:
            base = base.where(StressTest.backtest_id == backtest_id)  # type: ignore[arg-type]
            total_base = total_base.where(StressTest.backtest_id == backtest_id)  # type: ignore[arg-type]

        total = (await self.session.execute(total_base)).scalar_one()
        stmt = (
            base.order_by(StressTest.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    # --- 상태 전이 ---

    async def transition_to_running(
        self, stress_test_id: UUID, *, started_at: datetime
    ) -> int:
        """queued → running. 조건부."""
        result = await self.session.execute(
            update(StressTest)
            .where(StressTest.id == stress_test_id)  # type: ignore[arg-type]
            .where(StressTest.status == StressTestStatus.QUEUED)  # type: ignore[arg-type]
            .values(status=StressTestStatus.RUNNING, started_at=started_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def complete(
        self,
        stress_test_id: UUID,
        *,
        result: dict[str, Any],
    ) -> int:
        """running → completed."""
        update_result = await self.session.execute(
            update(StressTest)
            .where(StressTest.id == stress_test_id)  # type: ignore[arg-type]
            .where(StressTest.status == StressTestStatus.RUNNING)  # type: ignore[arg-type]
            .values(
                status=StressTestStatus.COMPLETED,
                result=result,
                completed_at=datetime.now(UTC),
            )
        )
        return update_result.rowcount or 0  # type: ignore[attr-defined]

    async def fail(
        self,
        stress_test_id: UUID,
        *,
        error: str,
        where_status: StressTestStatus | None = None,
    ) -> int:
        """→ failed. where_status 미지정 시 queued/running 허용."""
        stmt = (
            update(StressTest)
            .where(StressTest.id == stress_test_id)  # type: ignore[arg-type]
            .values(
                status=StressTestStatus.FAILED,
                error=error[:2000],
                completed_at=datetime.now(UTC),
            )
        )
        if where_status is not None:
            stmt = stmt.where(StressTest.status == where_status)  # type: ignore[arg-type]
        else:
            stmt = stmt.where(
                StressTest.status.in_(  # type: ignore[attr-defined]
                    [StressTestStatus.QUEUED, StressTestStatus.RUNNING]
                )
            )
        update_result = await self.session.execute(stmt)
        return update_result.rowcount or 0  # type: ignore[attr-defined]

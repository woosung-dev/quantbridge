"""Python 연구 데이터 접근. 작업 상태는 조건부 갱신으로 경합을 처리한다."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.python_strategy.models import PythonBacktest, PythonStrategy, PythonStrategyVersion, now


class PythonStrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, obj: PythonStrategy | PythonStrategyVersion | PythonBacktest) -> None:
        self.session.add(obj)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def lock_user(self, user_id: UUID) -> None:
        await self.session.execute(select(func.pg_advisory_xact_lock(user_id.int % (2**63))))

    async def strategy(self, strategy_id: UUID, user_id: UUID) -> PythonStrategy | None:
        result = await self.session.execute(
            select(PythonStrategy).where(
                col(PythonStrategy.id) == strategy_id, col(PythonStrategy.user_id) == user_id
            )
        )
        return result.scalar_one_or_none()

    async def version(self, version_id: UUID) -> PythonStrategyVersion | None:
        return await self.session.get(PythonStrategyVersion, version_id)

    async def strategies(self, user_id: UUID) -> list[tuple[PythonStrategy, PythonStrategyVersion]]:
        result = await self.session.execute(
            select(PythonStrategy, PythonStrategyVersion)
            .join(
                PythonStrategyVersion,
                col(PythonStrategy.version_id) == col(PythonStrategyVersion.id),
            )
            .where(col(PythonStrategy.user_id) == user_id)
            .order_by(col(PythonStrategy.updated_at).desc())
            .limit(100)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def run(self, run_id: UUID, user_id: UUID | None = None) -> PythonBacktest | None:
        stmt = select(PythonBacktest).where(col(PythonBacktest.id) == run_id)
        if user_id is not None:
            stmt = stmt.where(col(PythonBacktest.user_id) == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def runs(self, strategy_id: UUID, user_id: UUID) -> list[PythonBacktest]:
        stmt = (
            select(PythonBacktest)
            .where(
                col(PythonBacktest.strategy_id) == strategy_id,
                col(PythonBacktest.user_id) == user_id,
            )
            .order_by(col(PythonBacktest.created_at).desc())
            .limit(100)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def active_count(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(PythonBacktest)
            .where(
                col(PythonBacktest.user_id) == user_id,
                col(PythonBacktest.status).in_(["pending", "running"]),
            )
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def transition(
        self, run_id: UUID, previous: list[str], status: str, **values: Any
    ) -> bool:
        if status in {"completed", "failed", "cancelled"}:
            values["completed_at"] = now()
        stmt = (
            update(PythonBacktest)
            .where(
                col(PythonBacktest.id) == run_id,
                col(PythonBacktest.status).in_(previous),
            )
            .values(status=status, **values)
            .returning(col(PythonBacktest.id))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def reclaim_stale(self) -> int:
        from datetime import timedelta

        stmt = (
            update(PythonBacktest)
            .where(
                col(PythonBacktest.status).in_(["pending", "running"]),
                col(PythonBacktest.created_at) < now() - timedelta(minutes=30),
            )
            .values(status="failed", error="실행 제한 시간을 초과했습니다.", completed_at=now())
            .returning(col(PythonBacktest.id))
        )
        return len((await self.session.execute(stmt)).all())

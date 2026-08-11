"""strategy Repository. AsyncSession 유일 보유. commit() 은 Service 요청으로만."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import sharpe_sort_criteria
from src.strategy.models import ParseStatus, Strategy


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, strategy: Strategy) -> Strategy:
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def find_by_id(self, strategy_id: UUID) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy).where(Strategy.id == strategy_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_owner(self, strategy_id: UUID, owner_id: UUID) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,  # type: ignore[arg-type]
                    Strategy.user_id == owner_id,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        limit: int,
        offset: int,
        parse_status: ParseStatus | None = None,
        is_archived: bool = False,
        order_by: str = "updated_at",
        order: str = "desc",
    ) -> tuple[list[Strategy], int]:
        # and_() 로 조건 목록 조합 — *list[bool] arg-type 문제 회피
        filters = and_(
            Strategy.user_id == owner_id,  # type: ignore[arg-type]
            Strategy.is_archived == is_archived,  # type: ignore[arg-type]
        )
        if parse_status is not None:
            filters = and_(
                filters,
                Strategy.parse_status == parse_status,  # type: ignore[arg-type]
            )

        count_stmt = select(func.count()).select_from(Strategy).where(filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        latest_completed = (
            select(Backtest.strategy_id, Backtest.metrics)
            .where(Backtest.status == BacktestStatus.COMPLETED)
            .distinct(Backtest.strategy_id)
            .order_by(
                Backtest.strategy_id,
                Backtest.completed_at.desc().nulls_last(),  # type: ignore[union-attr]
                Backtest.created_at.desc(),  # type: ignore[attr-defined]
                Backtest.id.desc(),  # type: ignore[attr-defined]
            )
            .subquery()
        )
        latest_metrics = latest_completed.c.metrics
        sort_columns: dict[str, Any] = {
            "updated_at": Strategy.updated_at,
            "name": Strategy.name,
            "total_return": latest_metrics["total_return"].astext.cast(Numeric),
            "sharpe_ratio": latest_metrics["sharpe_ratio"].astext.cast(Numeric),
        }
        sort_expression = sort_columns[order_by]
        if order_by == "sharpe_ratio":
            order_criteria = sharpe_sort_criteria(
                sort_expression,
                order=order,
                convention=latest_metrics["sharpe_convention"].astext,
            )
        else:
            primary_order = sort_expression.asc() if order == "asc" else sort_expression.desc()
            if order_by == "total_return":
                primary_order = primary_order.nulls_last()
            order_criteria = [primary_order]

        items_stmt = (
            select(Strategy)
            .outerjoin(latest_completed, latest_completed.c.strategy_id == Strategy.id)
            .where(filters)
            .order_by(
                *order_criteria,
                Strategy.updated_at.desc(),  # type: ignore[attr-defined]
                Strategy.id.desc(),  # type: ignore[attr-defined]
            )
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, int(total)

    async def update(self, strategy: Strategy) -> Strategy:
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def delete(self, strategy_id: UUID) -> None:
        await self.session.execute(
            delete(Strategy).where(Strategy.id == strategy_id)  # type: ignore[arg-type]
        )

    async def archive_all_by_owner(self, owner_id: UUID) -> None:
        """user.deleted Webhook 시 해당 사용자의 모든 Strategy를 archive."""
        await self.session.execute(
            update(Strategy)
            .where(Strategy.user_id == owner_id)  # type: ignore[arg-type]
            .values(is_archived=True)
        )

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

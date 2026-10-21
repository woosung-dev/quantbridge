"""고정 리스크 원장의 CAS와 진입 주문 귀속을 같은 트랜잭션으로 저장한다."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.trading.models import LiveRiskState, LiveSignalSession, Order, OrderState


class CodeRiskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, session_id: UUID) -> LiveRiskState | None:
        result = await self.session.execute(
            select(LiveRiskState)
            .where(col(LiveRiskState.session_id) == session_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_entry_order(self, session_id: UUID, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .join(LiveSignalSession, col(LiveSignalSession.strategy_id) == col(Order.strategy_id))
            .where(
                col(LiveSignalSession.id) == session_id,
                col(LiveSignalSession.exchange_account_id) == col(Order.exchange_account_id),
                col(LiveSignalSession.symbol) == col(Order.symbol),
                col(Order.id) == order_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_if_absent(self, state: LiveRiskState) -> bool:
        result = await self.session.execute(
            insert(LiveRiskState)
            .values(**state.model_dump())
            .on_conflict_do_nothing(index_elements=["session_id"])
            .returning(col(LiveRiskState.session_id))
        )
        return result.scalar_one_or_none() is not None

    async def compare_and_swap(self, state: LiveRiskState, expected_revision: int) -> bool:
        values = state.model_dump(exclude={"session_id"})
        values.update(revision=expected_revision + 1, updated_at=datetime.now(UTC))
        result = await self.session.execute(
            update(LiveRiskState)
            .where(
                col(LiveRiskState.session_id) == state.session_id,
                col(LiveRiskState.revision) == expected_revision,
            )
            .values(**values)
            .returning(col(LiveRiskState.session_id))
            .execution_options(synchronize_session=False)
        )
        return result.scalar_one_or_none() is not None

    async def attach_entry(self, state: LiveRiskState, provisional_stop: Decimal) -> bool:
        result = await self.session.execute(
            update(Order)
            .where(
                col(Order.id) == state.entry_order_id,
                col(Order.state) == OrderState.pending,
                col(Order.risk_context).is_(None),
            )
            .values(
                risk_context={
                    "session_id": str(state.session_id),
                    "generation": state.generation,
                    "role": "entry",
                },
                stop_loss=provisional_stop,
            )
            .returning(col(Order.id))
            .execution_options(synchronize_session=False)
        )
        return result.scalar_one_or_none() is not None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

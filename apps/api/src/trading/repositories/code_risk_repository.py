"""고정 리스크 원장의 CAS와 진입 주문 귀속을 같은 트랜잭션으로 저장한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.strategy.models import StrategyVersion
from src.trading.models import (
    CodeRiskCommand,
    ExchangeAccount,
    LiveRiskState,
    LiveSignalSession,
    Order,
    OrderState,
)


class CodeRiskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire_entry_admission(self, session_id: UUID) -> bool:
        """코드 신규 진입 정본. True 뒤 영속 진입 예약/상태 전이 commit까지 같은 TX다."""
        from src.trading.repositories.live_signal_session_repository import (
            LiveSignalSessionRepository,
        )

        live = await self.get_session(session_id)
        if live is None:
            return False
        return await LiveSignalSessionRepository(self.session).acquire_code_symbol_admission(
            live.exchange_account_id, live.symbol, is_code=True, session_id=session_id
        )

    async def has_unsettled_exit_for_account(self, account_id: UUID) -> bool:
        from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository

        return await ExchangeAccountRepository(self.session).has_unsettled_code_exit(account_id)

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
            .execution_options(populate_existing=True)
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

    async def get_session(self, session_id: UUID) -> LiveSignalSession | None:
        return (
            await self.session.execute(
                select(LiveSignalSession).where(col(LiveSignalSession.id) == session_id)
            )
        ).scalar_one_or_none()

    async def get_version(self, version_id: UUID) -> StrategyVersion | None:
        return (
            await self.session.execute(
                select(StrategyVersion).where(col(StrategyVersion.id) == version_id)
            )
        ).scalar_one_or_none()

    async def get_account(self, account_id: UUID) -> ExchangeAccount | None:
        return (
            await self.session.execute(
                select(ExchangeAccount).where(col(ExchangeAccount.id) == account_id)
            )
        ).scalar_one_or_none()

    async def enqueue_commands(self, commands: list[CodeRiskCommand]) -> None:
        for command in commands:
            await self.session.execute(
                insert(CodeRiskCommand)
                .values(**command.model_dump())
                .on_conflict_do_nothing(index_elements=["key"])
            )

    async def claim_command(self, session_id: UUID, token: UUID) -> CodeRiskCommand | None:
        """외부 IO 전 commit하는 짧은 세션별 claim이다. lease 중 다른 명령은 못 잡는다."""
        locked = await self.session.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"code-risk:{session_id}"},
        )
        if not locked:
            return None
        now = datetime.now(UTC)
        running = (
            await self.session.execute(
                select(CodeRiskCommand)
                .where(
                    col(CodeRiskCommand.session_id) == session_id,
                    col(CodeRiskCommand.status) == "running",
                    col(CodeRiskCommand.lease_until) > now,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if running is not None:
            return None
        candidate = (
            await self.session.execute(
                select(CodeRiskCommand)
                .where(
                    col(CodeRiskCommand.session_id) == session_id,
                    or_(
                        col(CodeRiskCommand.status) == "pending",
                        and_(
                            col(CodeRiskCommand.status) == "running",
                            col(CodeRiskCommand.lease_until) <= now,
                        ),
                    ),
                )
                .order_by(
                    case(
                        (col(CodeRiskCommand.kind) == "flatten", 0),
                        (col(CodeRiskCommand.kind) == "cancel_entry", 1),
                        else_=2,
                    ),
                    col(CodeRiskCommand.created_at),
                    col(CodeRiskCommand.key),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if candidate is None:
            return None
        candidate.status = "running"
        candidate.lease_token = token
        candidate.lease_until = now + timedelta(seconds=60)
        candidate.attempts += 1
        await self.session.flush()
        return CodeRiskCommand(**candidate.model_dump())

    async def finish_command(
        self,
        key: str,
        token: UUID,
        *,
        status: str,
        result: dict[str, object] | None = None,
        error: str | None = None,
    ) -> bool:
        statement = (
            update(CodeRiskCommand)
            .where(
                col(CodeRiskCommand.key) == key,
                col(CodeRiskCommand.lease_token) == token,
                col(CodeRiskCommand.status) == "running",
            )
            .values(status=status, result=result, error=error, lease_until=None, lease_token=None)
            .returning(col(CodeRiskCommand.key))
            .execution_options(synchronize_session=False)
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def get_order(self, order_id: UUID) -> Order | None:
        return (
            await self.session.execute(
                select(Order)
                .where(col(Order.id) == order_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def child_orders(self, session_id: UUID, generation: int) -> list[Order]:
        result = await self.session.execute(
            select(Order).where(
                col(Order.risk_context)["session_id"].astext == str(session_id),
                col(Order.risk_context)["generation"].astext == str(generation),
                col(Order.reduce_only).is_(True),
            )
        )
        return list(result.scalars().all())

    async def pending_sessions(self, account_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(col(LiveRiskState.session_id))
            .join(LiveSignalSession, col(LiveSignalSession.id) == col(LiveRiskState.session_id))
            .where(col(LiveSignalSession.exchange_account_id) == account_id)
        )
        return list(result.scalars().all())

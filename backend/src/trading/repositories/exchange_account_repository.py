# trading repository — ExchangeAccount + API key AES-256 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import ExchangeAccount, ExchangeName


class ExchangeAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, account: ExchangeAccount) -> ExchangeAccount:
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_by_id(self, account_id: UUID) -> ExchangeAccount | None:
        result = await self.session.execute(
            select(ExchangeAccount).where(ExchangeAccount.id == account_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> Sequence[ExchangeAccount]:
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.user_id == user_id)  # type: ignore[arg-type]
            .order_by(ExchangeAccount.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def list_by_exchange(self, exchange: ExchangeName) -> Sequence[ExchangeAccount]:
        """거래소별 전 계정. 스윕이 우리 주문 유무와 무관하게 계정을 독립 열거하기 위해 필요하다."""
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.exchange == exchange)  # type: ignore[arg-type]
            .order_by(ExchangeAccount.created_at.asc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def delete(self, account_id: UUID) -> int:
        result = await self.session.execute(
            delete(ExchangeAccount).where(ExchangeAccount.id == account_id)  # type: ignore[arg-type]
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

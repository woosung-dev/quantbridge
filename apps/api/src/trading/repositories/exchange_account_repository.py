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
        """PK 조회 — identity map 을 타는 `session.get` 을 쓴다.

        ★종전에는 `select(...).where(id == ...)` 였다. 같은 트랜잭션에서 이미 로드된 계정도
        매번 DB 를 다시 쳤고, `tasks/trading.py` 는 그 비용을 피하려 세션을 직접 조회해
        Repository 를 우회하고 있었다(2026-09-06 아키텍처 감사, 6곳). PK 조회는
        `session.get` 이 정석이고 선례도 있다 — `kill_switch_event_repository.py:34`.
        """
        return await self.session.get(ExchangeAccount, account_id)

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

    async def list_without_exchange_uid(self) -> Sequence[ExchangeAccount]:
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.exchange_uid.is_(None))  # type: ignore[union-attr]
            .order_by(ExchangeAccount.created_at.asc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def list_by_exchange_uid(self, exchange_uid: str) -> Sequence[ExchangeAccount]:
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.exchange_uid == exchange_uid)  # type: ignore[arg-type]
            .order_by(ExchangeAccount.created_at.asc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def delete(self, account_id: UUID) -> int:
        result = await self.session.execute(
            delete(ExchangeAccount).where(ExchangeAccount.id == account_id)  # type: ignore[arg-type]
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

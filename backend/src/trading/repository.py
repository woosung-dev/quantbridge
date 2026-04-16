"""trading Repository 레이어. AsyncSession 유일 보유. commit은 Service 요청으로만.

네이밍 컨벤션:
- `save()` = add + flush (ID/created_at 채워진 동일 인스턴스 반환). upsert-by-identity:
  수정 후 재저장도 같은 메서드. Sprint 4는 create/update 분리 — Sprint 6은 단일화.
- T8 OrderRepository에서 Sprint 4 BacktestRepository의 3-guard `transition_*` 패턴 계승 예정.
"""
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import ExchangeAccount


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

    async def delete(self, account_id: UUID) -> int:
        result = await self.session.execute(
            delete(ExchangeAccount).where(ExchangeAccount.id == account_id)  # type: ignore[arg-type]
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

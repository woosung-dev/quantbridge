"""auth 도메인 Repository. AsyncSession 유일 보유자."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_clerk_id(self, clerk_user_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))  # type: ignore[arg-type]
        return result.scalar_one_or_none()

    async def insert_if_absent(
        self,
        clerk_user_id: str,
        email: str | None = None,
        username: str | None = None,
    ) -> User:
        """INSERT ... ON CONFLICT DO NOTHING + SELECT 재조회.

        동일 clerk_user_id로 병렬 요청이 와도 race 없이 1개만 존재하도록 보장.
        """
        stmt = pg_insert(User).values(
            clerk_user_id=clerk_user_id,
            email=email,
            username=username,
        ).on_conflict_do_nothing(index_elements=["clerk_user_id"])
        await self.session.execute(stmt)
        # 삽입됐든 아니든 최종 row 반환
        user = await self.find_by_clerk_id(clerk_user_id)
        assert user is not None
        return user

    async def upsert_from_webhook(
        self,
        clerk_user_id: str,
        email: str | None = None,
        username: str | None = None,
        country_code: str | None = None,
    ) -> User:
        """Webhook user.created/updated 처리.

        INSERT ... ON CONFLICT DO UPDATE — email/username/country_code 를 최신으로 덮어씀.
        country_code 는 Sprint 11 Phase A 에서 추가. public_metadata.country 기반.
        """
        stmt = (
            pg_insert(User)
            .values(
                clerk_user_id=clerk_user_id,
                email=email,
                username=username,
                country_code=country_code,
            )
            .on_conflict_do_update(
                index_elements=["clerk_user_id"],
                set_={
                    "email": email,
                    "username": username,
                    "country_code": country_code,
                },
            )
        )
        await self.session.execute(stmt)
        # identity map 갱신: ON CONFLICT DO UPDATE는 ORM을 우회하므로
        # 세션 캐시에 스테일 객체가 남을 수 있다. expire_all로 강제 재조회.
        self.session.expire_all()
        user = await self.find_by_clerk_id(clerk_user_id)
        assert user is not None
        return user

    async def update_profile(
        self,
        user_id: UUID,
        email: str | None,
        username: str | None,
    ) -> User:
        user = await self.find_by_id(user_id)
        assert user is not None
        user.email = email
        user.username = username
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_inactive(self, user_id: UUID) -> None:
        user = await self.find_by_id(user_id)
        if user is None:
            return
        user.is_active = False
        self.session.add(user)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

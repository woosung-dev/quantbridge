"""auth 도메인 Repository. AsyncSession 유일 보유자."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_auth_subject(self, auth_subject: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.auth_subject == auth_subject)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))  # type: ignore[arg-type]
        return result.scalar_one_or_none()

    async def get_created_at(self, user_id: UUID) -> datetime | None:
        """readiness gate 용 — user.created_at 조회 (없으면 None)."""
        user = await self.find_by_id(user_id)
        return user.created_at if user is not None else None

    async def insert_if_absent(
        self,
        auth_subject: str,
        email: str | None = None,
        username: str | None = None,
        country_code: str | None = None,
    ) -> User:
        """INSERT ... ON CONFLICT DO NOTHING + SELECT 재조회.

        동일 auth_subject 로 병렬 요청이 와도 race 없이 1개만 존재하도록 보장.
        """
        stmt = (
            pg_insert(User)
            .values(
                auth_subject=auth_subject,
                email=email,
                username=username,
                country_code=country_code,
            )
            .on_conflict_do_nothing(index_elements=["auth_subject"])
        )
        await self.session.execute(stmt)
        # 삽입됐든 아니든 최종 row 반환
        user = await self.find_by_auth_subject(auth_subject)
        assert user is not None
        return user

    async def update_profile(
        self,
        user_id: UUID,
        email: str | None,
        username: str | None,
        country_code: str | None = None,
    ) -> User:
        """JWT payload 가 실어 온 프로필을 반영한다.

        ★`country_code` 는 **None 이면 덮어쓰지 않는다** — 토큰에 국가가 없는 경로(기존 사용자,
        헤더 없는 로컬 개발)가 이미 적힌 값을 지우면 안 된다.
        """
        user = await self.find_by_id(user_id)
        assert user is not None
        user.email = email
        user.username = username
        if country_code is not None:
            user.country_code = country_code
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

"""auth 도메인 Depends() 조립."""
from __future__ import annotations

from clerk_backend_api import Clerk
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import UserRepository
from src.auth.schemas import CurrentUser
from src.auth.service import UserService
from src.common.database import get_async_session
from src.core.config import settings
from src.realtime.auth import authenticate_clerk_request


def _clerk_client() -> Clerk:
    """모듈 스코프 싱글톤 회피 — 테스트 monkeypatch 용이."""
    return Clerk(bearer_auth=settings.clerk_secret_key.get_secret_value())


async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    session: AsyncSession = Depends(get_async_session),
) -> UserService:
    # Strategy archive를 위해 StrategyRepository를 동일 session으로 주입
    from src.strategy.repository import StrategyRepository

    strategy_repo = StrategyRepository(session)
    return UserService(user_repo=user_repo, strategy_repo=strategy_repo)


async def get_current_user(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> CurrentUser:
    """Bearer JWT 검증 + lazy-create."""
    return await authenticate_clerk_request(request, service, clerk=_clerk_client())

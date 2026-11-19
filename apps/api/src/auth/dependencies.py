"""auth 도메인 Depends() 조립."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import UserRepository
from src.auth.schemas import CurrentUser
from src.auth.service import UserService
from src.common.database import async_session_factory, get_async_session
from src.realtime.auth import authenticate_request


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserRepository:
    return UserRepository(session)


async def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserService:
    return _build_user_service(user_repo, session)


def _build_user_service(user_repo: UserRepository, session: AsyncSession) -> UserService:
    # Strategy archive를 위해 StrategyRepository를 동일 session으로 주입.
    # ★2026-08-15 surface-truth (S3) — 탈퇴가 **돈을 멈추려면** 라이브 세션·웹훅 시크릿
    #   두 레포도 필요하다. 넷 다 **같은 session** 이어야 `UserService` 의 단일 commit 이
    #   전부를 한 트랜잭션으로 닫는다(AGENTS.md §3 「크로스 레포지토리 트랜잭션」).
    from src.strategy.repository import StrategyRepository
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository

    return UserService(
        user_repo=user_repo,
        strategy_repo=StrategyRepository(session),
        live_session_repo=LiveSignalSessionRepository(session),
        webhook_secret_repo=WebhookSecretRepository(session),
    )


@asynccontextmanager
async def user_service_scope() -> AsyncIterator[UserService]:
    """블록이 끝나면 세션을 닫는 `UserService` — **오래 사는 WebSocket 의 인증 전용**.

    `UserServiceDep` 은 세션 수명이 핸들러 수명이다. WebSocket 핸들러는 소켓이 열려 있는 내내
    돌기 때문에, 인증 조회가 연 트랜잭션이 풀 커넥션 하나를 소켓 수명만큼 쥐었다
    (idle in transaction — 보안 감사 2026-11-19). 인증이 끝나면 바로 돌려준다.
    """
    async with async_session_factory() as session:
        yield _build_user_service(UserRepository(session), session)


# 라우터·의존성에서 반복되는 주입을 한 줄로 쓰기 위한 별칭.
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user(
    request: Request,
    service: UserServiceDep,
) -> CurrentUser:
    """Bearer JWT 검증 + lazy-create — 검증기는 `realtime/auth.py` 하나뿐이다(ADR-034)."""
    return await authenticate_request(request, service)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]

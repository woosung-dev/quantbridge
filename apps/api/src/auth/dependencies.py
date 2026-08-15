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


async def get_current_user(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> CurrentUser:
    """Bearer JWT 검증 + lazy-create."""
    return await authenticate_clerk_request(request, service, clerk=_clerk_client())

"""waitlist Depends() 조립."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUserDep
from src.auth.schemas import CurrentUser
from src.common.database import get_async_session
from src.core.config import settings
from src.waitlist.email_service import EmailService
from src.waitlist.exceptions import AdminOnlyError
from src.waitlist.repository import WaitlistRepository
from src.waitlist.service import ServiceConfig, WaitlistService
from src.waitlist.token_service import InviteTokenService


async def get_waitlist_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> WaitlistRepository:
    return WaitlistRepository(session)


def get_token_service() -> InviteTokenService:
    secret = settings.waitlist_token_secret.get_secret_value()
    # dev/test 에서 secret 미설정 시 placeholder 주입 (실 발행은 production 환경 변수 필수).
    if not secret:
        secret = "insecure-dev-placeholder-do-not-use-in-prod-00000"  # noqa: S105
    return InviteTokenService(secret=secret)


def get_email_service() -> EmailService:
    api_key = settings.resend_api_key.get_secret_value()
    # dev 환경 기본값 — send_invite_email 호출 시점에 오류 아닌 placeholder.
    # 테스트는 이 factory 를 override.
    # ★[BL-072] 발신 주소를 설정에서 읽는다 — 종전에는 `EmailService` 기본 인자
    #   (`…@quantbridge.app`)가 유일한 값이라 실도메인으로 바꿀 경로가 아예 없었다.
    return EmailService(
        api_key=api_key or "dev-empty-key",
        from_address=settings.resend_from_address,
    )


async def get_waitlist_service(
    repo: Annotated[WaitlistRepository, Depends(get_waitlist_repository)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
    token_service: Annotated[InviteTokenService, Depends(get_token_service)],
) -> WaitlistService:
    return WaitlistService(
        repo=repo,
        email_service=email_service,
        token_service=token_service,
        config=ServiceConfig(invite_base_url=settings.waitlist_invite_base_url),
    )


# 라우터에서 반복되는 서비스 주입 별칭.
WaitlistServiceDep = Annotated[WaitlistService, Depends(get_waitlist_service)]


async def require_admin(
    current_user: CurrentUserDep,
) -> CurrentUser:
    """Admin 권한 검증 — settings.waitlist_admin_emails 화이트리스트.

    Beta 초기 수동 운영용. H3 이후 사용자 role 필드로 이전 예정.
    """
    allowed = settings.waitlist_admin_emails
    user_email = (current_user.email or "").strip().lower()
    if not allowed or not user_email or user_email not in allowed:
        raise AdminOnlyError()
    return current_user

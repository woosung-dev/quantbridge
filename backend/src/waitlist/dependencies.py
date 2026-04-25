"""waitlist Depends() 조립."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.database import get_async_session
from src.core.config import settings
from src.waitlist.email_service import EmailService
from src.waitlist.exceptions import AdminOnlyError
from src.waitlist.repository import WaitlistRepository
from src.waitlist.service import ServiceConfig, WaitlistService
from src.waitlist.token_service import InviteTokenService


async def get_waitlist_repository(
    session: AsyncSession = Depends(get_async_session),
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
    return EmailService(api_key=api_key or "dev-empty-key")


async def get_waitlist_service(
    repo: WaitlistRepository = Depends(get_waitlist_repository),
    email_service: EmailService = Depends(get_email_service),
    token_service: InviteTokenService = Depends(get_token_service),
) -> WaitlistService:
    return WaitlistService(
        repo=repo,
        email_service=email_service,
        token_service=token_service,
        config=ServiceConfig(invite_base_url=settings.waitlist_invite_base_url),
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Admin 권한 검증 — settings.waitlist_admin_emails 화이트리스트.

    Beta 초기 수동 운영용. H3 이후 Clerk publicMetadata.role=admin 으로 이전 예정.
    """
    allowed = settings.waitlist_admin_emails
    user_email = (current_user.email or "").strip().lower()
    if not allowed or not user_email or user_email not in allowed:
        raise AdminOnlyError()
    return current_user

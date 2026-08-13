"""waitlist Service — form validation + token + email 조율."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.waitlist.email_service import EmailService
from src.waitlist.exceptions import (
    DuplicateEmailError,
    WaitlistNotFoundError,
)
from src.waitlist.models import WaitlistApplication, WaitlistStatus
from src.waitlist.repository import WaitlistRepository
from src.waitlist.schemas import (
    AdminApproveResponse,
    AdminWaitlistListResponse,
    CreateWaitlistApplicationRequest,
    InviteTokenVerifyResponse,
    WaitlistApplicationAcceptedResponse,
    WaitlistApplicationResponse,
)
from src.waitlist.token_service import InviteTokenService

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceConfig:
    """Service 에 주입되는 런타임 설정."""

    invite_base_url: str  # frontend invite landing base e.g. https://quantbridge.app/invite


class WaitlistService:
    def __init__(
        self,
        *,
        repo: WaitlistRepository,
        email_service: EmailService,
        token_service: InviteTokenService,
        config: ServiceConfig,
    ) -> None:
        self.repo = repo
        self.email_service = email_service
        self.token_service = token_service
        self.config = config

    # ---------------- Public ----------------

    async def submit_application(
        self,
        data: CreateWaitlistApplicationRequest,
    ) -> WaitlistApplicationAcceptedResponse:
        """이메일 unique 체크 → create → 202. email 발송은 admin approve 시점."""
        normalized_email = str(data.email).strip().lower()
        existing = await self.repo.find_by_email(normalized_email)
        if existing is not None:
            raise DuplicateEmailError()

        application = WaitlistApplication(
            email=normalized_email,
            tv_subscription=data.tv_subscription,
            exchange_capital=data.exchange_capital,
            pine_experience=data.pine_experience,
            existing_tool=data.existing_tool,
            pain_point=data.pain_point,
            status=WaitlistStatus.pending,
        )
        try:
            saved = await self.repo.create(application)
            await self.repo.commit()
        except IntegrityError as exc:
            # race 로 동일 email unique 위반 → 409
            await self.repo.rollback()
            raise DuplicateEmailError() from exc
        return WaitlistApplicationAcceptedResponse(
            id=saved.id,
            status=saved.status,
        )

    async def verify_invite_token(self, token: str) -> InviteTokenVerifyResponse:
        """Token 검증 + DB state 확인."""
        payload = self.token_service.verify(token)
        existing = await self.repo.find_by_invite_token(token)
        if existing is None:
            raise WaitlistNotFoundError()
        return InviteTokenVerifyResponse(
            email=payload.email,
            status=existing.status,
        )

    # ---------------- Admin ----------------

    async def admin_list(
        self,
        *,
        status: WaitlistStatus | None,
        limit: int,
        offset: int,
    ) -> AdminWaitlistListResponse:
        items, total = await self.repo.list_by_status(
            status=status, limit=limit, offset=offset
        )
        return AdminWaitlistListResponse(
            items=[WaitlistApplicationResponse.model_validate(i) for i in items],
            total=total,
        )

    async def admin_approve(self, application_id: UUID) -> AdminApproveResponse:
        """1) 존재 확인 → 2) token 발급 → 3) email 발송 → 4) DB invited 전환."""
        application = await self.repo.find_by_id(application_id)
        if application is None:
            raise WaitlistNotFoundError()

        token = self.token_service.issue(application.email)
        invite_url = f"{self.config.invite_base_url.rstrip('/')}/{token}"
        # Email 발송 실패 시 EmailSendError (502). DB 는 아직 전환되지 않았으므로 rollback 불필요.
        await self.email_service.send_invite_email(
            to_email=application.email,
            invite_url=invite_url,
        )
        updated = await self.repo.mark_invited(application, invite_token=token)
        await self.repo.commit()
        return AdminApproveResponse(
            id=updated.id,
            status=updated.status,
            email=updated.email,
            invite_sent_at=updated.invite_sent_at,
        )

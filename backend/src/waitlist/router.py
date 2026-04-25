"""waitlist HTTP 라우터."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.waitlist.dependencies import (
    get_waitlist_service,
    require_admin,
)
from src.waitlist.models import WaitlistStatus
from src.waitlist.schemas import (
    AdminApproveResponse,
    AdminWaitlistListResponse,
    CreateWaitlistApplicationRequest,
    InviteTokenVerifyResponse,
    WaitlistApplicationAcceptedResponse,
)
from src.waitlist.service import WaitlistService

router = APIRouter(tags=["waitlist"])

# ---------------- Public ----------------


@router.post(
    "/waitlist",
    status_code=202,
    response_model=WaitlistApplicationAcceptedResponse,
)
@limiter.limit("5/hour")
async def submit_application(
    request: Request,  # slowapi 필수
    response: Response,  # slowapi headers_enabled=True 시 필수 (X-RateLimit-* 주입)
    data: CreateWaitlistApplicationRequest,
    service: WaitlistService = Depends(get_waitlist_service),
) -> WaitlistApplicationAcceptedResponse:
    return await service.submit_application(data)


@router.get(
    "/waitlist/invite/{token}",
    response_model=InviteTokenVerifyResponse,
)
@limiter.limit("10/minute")
async def verify_invite(
    request: Request,
    response: Response,  # slowapi headers_enabled=True 시 필수
    token: str = Path(..., min_length=10, max_length=512),
    service: WaitlistService = Depends(get_waitlist_service),
) -> InviteTokenVerifyResponse:
    return await service.verify_invite_token(token)


# ---------------- Admin ----------------


@router.get(
    "/admin/waitlist",
    response_model=AdminWaitlistListResponse,
)
async def admin_list(
    status: WaitlistStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: CurrentUser = Depends(require_admin),
    service: WaitlistService = Depends(get_waitlist_service),
) -> AdminWaitlistListResponse:
    return await service.admin_list(status=status, limit=limit, offset=offset)


@router.post(
    "/admin/waitlist/{application_id}/approve",
    response_model=AdminApproveResponse,
)
async def admin_approve(
    application_id: UUID = Path(...),
    _admin: CurrentUser = Depends(require_admin),
    service: WaitlistService = Depends(get_waitlist_service),
) -> AdminApproveResponse:
    return await service.admin_approve(application_id)

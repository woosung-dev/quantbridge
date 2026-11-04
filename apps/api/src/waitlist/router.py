"""waitlist HTTP 라우터."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.waitlist.dependencies import WaitlistServiceDep, require_admin
from src.waitlist.models import WaitlistStatus
from src.waitlist.schemas import (
    AdminApproveResponse,
    AdminWaitlistListResponse,
    CreateWaitlistApplicationRequest,
    InviteTokenVerifyResponse,
    WaitlistApplicationAcceptedResponse,
)

router = APIRouter(tags=["waitlist"])

# ---------------- Public ----------------


@router.post(
    "/waitlist",
    status_code=202,
)
@limiter.limit("5/hour")
async def submit_application(
    request: Request,  # slowapi 필수
    response: Response,  # slowapi headers_enabled=True 시 필수 (X-RateLimit-* 주입)
    data: CreateWaitlistApplicationRequest,
    service: WaitlistServiceDep,
) -> WaitlistApplicationAcceptedResponse:
    return await service.submit_application(data)


@router.get("/waitlist/invite/{token}")
@limiter.limit("10/minute")
async def verify_invite(
    request: Request,
    response: Response,  # slowapi headers_enabled=True 시 필수
    token: Annotated[str, Path(min_length=10, max_length=512)],
    service: WaitlistServiceDep,
) -> InviteTokenVerifyResponse:
    return await service.verify_invite_token(token)


# ---------------- Admin ----------------


@router.get("/admin/waitlist")
async def admin_list(
    _admin: Annotated[CurrentUser, Depends(require_admin)],
    service: WaitlistServiceDep,
    status: Annotated[WaitlistStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminWaitlistListResponse:
    return await service.admin_list(status=status, limit=limit, offset=offset)


@router.post("/admin/waitlist/{application_id}/approve")
async def admin_approve(
    application_id: Annotated[UUID, Path()],
    _admin: Annotated[CurrentUser, Depends(require_admin)],
    service: WaitlistServiceDep,
) -> AdminApproveResponse:
    return await service.admin_approve(application_id)

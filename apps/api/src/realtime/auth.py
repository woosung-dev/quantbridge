# HTTP와 WebSocket에서 공유하는 Clerk 인증 검증 함수.
from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions, Requestish

from src.auth.exceptions import InvalidTokenError, UserInactiveError
from src.auth.schemas import CurrentUser
from src.auth.service import UserService
from src.core.config import settings


def _clerk_client() -> Clerk:
    """요청별 Clerk 클라이언트를 생성한다."""
    return Clerk(bearer_auth=settings.clerk_secret_key.get_secret_value())


async def authenticate_clerk_request(
    request: Requestish,
    service: UserService,
    clerk: Clerk | None = None,
) -> CurrentUser:
    """Clerk request를 검증하고 로컬 사용자를 lazy-create 한다."""
    client = clerk or _clerk_client()
    req_state = client.authenticate_request(
        request,
        AuthenticateRequestOptions(authorized_parties=[settings.frontend_url]),
    )
    if not req_state.is_signed_in:
        reason = getattr(req_state.reason, "name", "unknown")
        raise InvalidTokenError(reason=reason)

    payload = req_state.payload or {}
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise InvalidTokenError(reason="missing_sub")

    user = await service.get_or_create(
        clerk_user_id=clerk_user_id,
        email=payload.get("email"),
        username=payload.get("username"),
    )
    if not user.is_active:
        raise UserInactiveError()

    return CurrentUser.model_validate(user)


async def authenticate_clerk_token(
    token: str,
    service: UserService,
    clerk: Clerk | None = None,
) -> CurrentUser:
    """WebSocket auth 메시지의 Bearer 토큰을 Clerk로 검증한다."""
    request = cast(
        Requestish,
        SimpleNamespace(headers={"Authorization": f"Bearer {token}"}),
    )
    return await authenticate_clerk_request(request, service, clerk)

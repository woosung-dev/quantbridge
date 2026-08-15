"""auth HTTP 라우터."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.auth.dependencies import get_current_user, get_user_service
from src.auth.schemas import CurrentUser, UserResponse
from src.auth.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.user_repo.find_by_id(current_user.id)
    assert user is not None  # dependency가 보장
    return UserResponse.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    """탈퇴 — 계정을 잠그고 전략 archive · 라이브 세션 정지 · 웹훅 시크릿 revoke 를 한 번에.

    ★**이 엔드포인트가 종전 Clerk `user.deleted` 웹훅의 자리다**(ADR-034). 그 웹훅은 「돈을
    멈추는」 유일한 입구였고(2026-08-15 surface-truth S3), 공급자를 바꾸면서 입구가 사라질
    뻔했다. 인증이 필요하므로 **본인만** 자기 계정을 닫을 수 있다.

    ★호출 순서 주의 — 클라이언트는 이 API 를 **먼저** 부르고 그다음 Better Auth 사용자 삭제를
    한다. 뒤집으면 세션이 먼저 사라져 이 API 를 부를 자격이 없어진다.
    """
    await service.deactivate_account(current_user.id)

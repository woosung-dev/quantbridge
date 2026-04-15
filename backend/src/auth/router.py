"""auth HTTP 라우터."""
from __future__ import annotations

from fastapi import APIRouter, Depends

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

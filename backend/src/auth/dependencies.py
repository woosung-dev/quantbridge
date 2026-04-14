from fastapi import Header, HTTPException, status

from src.auth.schemas import CurrentUser


async def get_current_user(
    authorization: str = Header(..., description="Bearer <Clerk JWT>"),
) -> CurrentUser:
    """Clerk JWT 검증. 실제 검증 로직은 Stage 3에서 clerk-backend-api로 구현."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    # TODO(stage3): clerk-backend-api SDK로 세션/JWT 검증 후 CurrentUser 채우기
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Clerk JWT verification not implemented yet (scaffold phase)",
    )

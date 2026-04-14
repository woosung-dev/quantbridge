from pydantic import BaseModel


class CurrentUser(BaseModel):
    """검증된 Clerk 세션에서 파생된 사용자 정보."""

    user_id: str
    email: str | None = None
    session_id: str | None = None

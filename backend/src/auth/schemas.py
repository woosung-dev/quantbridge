"""auth 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CurrentUser(BaseModel):
    """검증된 Clerk 세션 + DB User 매핑 결과."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clerk_user_id: str
    email: str | None = None
    username: str | None = None
    is_active: bool = True
    session_id: str | None = None


class UserResponse(BaseModel):
    """GET /auth/me 응답 DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clerk_user_id: str
    email: str | None
    username: str | None
    is_active: bool
    created_at: datetime

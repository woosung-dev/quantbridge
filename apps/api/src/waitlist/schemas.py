"""waitlist 도메인 Pydantic V2 스키마.

필드 validation 정책:
- tv_subscription: "pro", "pro_plus", "premium" 만 허용 (alert 기능 필수)
- exchange_capital: "under_1k", "1k_to_10k", "10k_to_100k", "over_100k"
- pine_experience: "none", "beginner", "intermediate", "expert"
- pain_point: 3~1000자 (실제 문제 의식 필터)
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from src.waitlist.models import WaitlistStatus

# Literal 로 ENUM 대체 — Pydantic 이 422 로 거절.
TVSubscription = Literal["pro", "pro_plus", "premium"]
ExchangeCapital = Literal["under_1k", "1k_to_10k", "10k_to_100k", "over_100k"]
PineExperience = Literal["none", "beginner", "intermediate", "expert"]


class CreateWaitlistApplicationRequest(BaseModel):
    """Public form submission. /waitlist POST body."""

    # EmailStr 대신 정규식 — `email-validator` 의존 추가 회피 (기존 스택 최소 영향).
    email: str = Field(
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="사용자 이메일 (unique)",
    )
    tv_subscription: TVSubscription = Field(
        description="TradingView 구독 등급 — Pro+ 이상 필수 (alert 발송 기능)",
    )
    exchange_capital: ExchangeCapital = Field(
        description="예치 가능 자본 규모 — 1k USD 이상 권장",
    )
    pine_experience: PineExperience = Field(description="Pine Script 경험 수준")
    existing_tool: str | None = Field(
        default=None,
        max_length=120,
        description="현재 사용 중인 자동매매 도구 (선택)",
    )
    pain_point: str = Field(
        min_length=3,
        max_length=1000,
        description="QuantBridge 로 해결하고 싶은 문제 (필수)",
    )

    @field_validator("existing_tool")
    @classmethod
    def _normalize_existing_tool(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    @field_validator("pain_point")
    @classmethod
    def _strip_pain_point(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3:
            raise ValueError("pain_point must be at least 3 characters")
        return stripped


class WaitlistApplicationResponse(BaseModel):
    """Admin/self 조회용 DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    tv_subscription: str
    exchange_capital: str
    pine_experience: str
    existing_tool: str | None
    pain_point: str
    status: WaitlistStatus
    invite_sent_at: AwareDatetime | None
    invited_at: AwareDatetime | None
    joined_at: AwareDatetime | None
    created_at: AwareDatetime


class WaitlistApplicationAcceptedResponse(BaseModel):
    """POST /waitlist 202 응답 — id + status 만 노출 (security)."""

    id: UUID
    status: WaitlistStatus


class AdminWaitlistListResponse(BaseModel):
    """GET /admin/waitlist."""

    items: list[WaitlistApplicationResponse]
    total: int


class AdminApproveResponse(BaseModel):
    """POST /admin/waitlist/{id}/approve."""

    id: UUID
    status: WaitlistStatus
    email: str
    invite_sent_at: AwareDatetime | None


class InviteTokenVerifyResponse(BaseModel):
    """GET /waitlist/invite/{token} — token 검증 + 사용자 이메일 노출."""

    email: str
    status: WaitlistStatus

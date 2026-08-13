"""auth 도메인 예외."""
from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class AuthError(AppException):
    """auth 도메인 베이스 예외."""


class InvalidTokenError(AuthError):
    """유효하지 않거나 만료된 Clerk 토큰."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "auth_invalid_token"
    detail = "Invalid or expired token"

    def __init__(self, reason: str = "Invalid or expired token") -> None:
        super().__init__(detail=reason)


class UserInactiveError(AuthError):
    """비활성화된 사용자 계정."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "auth_user_inactive"
    detail = "User account deactivated"


class WebhookSignatureError(AuthError):
    """Svix 서명 검증 실패."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "webhook_signature_invalid"
    detail = "Svix signature verification failed"


class GeoBlockedCountryError(AuthError):
    """Sprint 11 Phase A — 지원 제외 국가 (US/EU) 가입 차단.

    3 계층 방어의 L3 (Clerk webhook). L1 (Cloudflare WAF) + L2 (Next.js proxy.ts)
    통과한 경우에도 본 계층에서 거절. public_metadata.country 가 restricted set 에 포함되면 400.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    code = "geo_blocked_country"
    detail = "Country not supported"

    def __init__(self, country: str) -> None:
        super().__init__(detail=f"Country {country} is not supported. QuantBridge is currently available in Asia only.")

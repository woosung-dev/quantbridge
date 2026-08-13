"""waitlist 도메인 예외."""
from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class WaitlistError(AppException):
    """waitlist 도메인 베이스."""


class DuplicateEmailError(WaitlistError):
    """이미 등록된 이메일."""

    status_code = status.HTTP_409_CONFLICT
    code = "waitlist_duplicate_email"
    detail = "This email is already on the waitlist"


class WaitlistNotFoundError(WaitlistError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "waitlist_not_found"
    detail = "Waitlist application not found"


class InviteTokenInvalidError(WaitlistError):
    """서명 변조 / base64 오류."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "waitlist_invite_token_invalid"
    detail = "Invite token is invalid"


class InviteTokenExpiredError(WaitlistError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "waitlist_invite_token_expired"
    detail = "Invite token has expired"


class EmailSendError(WaitlistError):
    """Resend API 연속 실패 — tenacity retry 소진."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "waitlist_email_send_failed"
    detail = "Failed to send invite email"


class AdminOnlyError(WaitlistError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "waitlist_admin_only"
    detail = "This endpoint requires admin privileges"

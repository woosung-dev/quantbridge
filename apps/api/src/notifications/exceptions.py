"""notifications 도메인 예외."""

from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class NotificationsError(AppException):
    """notifications 도메인 베이스."""


class PushSubscriptionNotFoundError(NotificationsError):
    """없는 endpoint · 남의 endpoint 를 **같은 404** 로 접는다 — 존재 여부를 흘리지 않는다."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "push_subscription_not_found"
    detail = "Push subscription not found"


class PushDisabledError(NotificationsError):
    """VAPID 키가 없어 푸시가 꺼져 있다."""

    status_code = status.HTTP_409_CONFLICT
    code = "push_disabled"
    detail = "Web push is not configured on this server"

"""Resend API 기반 이메일 발송 서비스.

- httpx AsyncClient 직접 호출 (sdk 의존 없음, free tier 100/일).
- tenacity retry: 3 회 시도, exponential 1~10s.
- API docs: https://resend.com/docs/api-reference/emails/send-email
- 실패 시 EmailSendError (502) 전파.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.waitlist.exceptions import EmailSendError

_LOGGER = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class _RetryableError(Exception):
    """5xx / network error 로 재시도 대상."""


def _is_retryable_status(status_code: int) -> bool:
    return status_code >= 500 or status_code == 429


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((_RetryableError, httpx.TransportError)),
)
async def _send_once(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(
        RESEND_API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10.0,
    )
    if _is_retryable_status(response.status_code):
        _LOGGER.warning(
            "resend_retryable_error",
            extra={"status": response.status_code, "body": response.text[:200]},
        )
        raise _RetryableError(f"Resend {response.status_code}: {response.text[:200]}")
    if response.status_code >= 400:
        _LOGGER.error(
            "resend_permanent_error",
            extra={"status": response.status_code, "body": response.text[:200]},
        )
        raise EmailSendError(detail=f"Resend rejected email: {response.status_code}")
    parsed: dict[str, Any] = response.json()
    return parsed


class EmailService:
    """Resend wrapper — 단일 public `send_invite_email` API.

    테스트는 httpx.AsyncClient 에 MockTransport 주입해 실 네트워크 호출 없이 검증.
    """

    def __init__(
        self,
        *,
        api_key: str,
        from_address: str = "QuantBridge Waitlist <waitlist@quantbridge.app>",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Resend API key is empty")
        self._api_key = api_key
        self._from_address = from_address
        self._client = client

    async def send_invite_email(
        self,
        *,
        to_email: str,
        invite_url: str,
    ) -> None:
        """발송 성공 시 void, 실패 시 EmailSendError 전파."""
        payload: dict[str, Any] = {
            "from": self._from_address,
            "to": [to_email],
            "subject": "You're invited to QuantBridge Beta",
            "html": _render_invite_html(invite_url=invite_url),
            "text": _render_invite_text(invite_url=invite_url),
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            try:
                await _send_once(client, api_key=self._api_key, payload=payload)
            except _RetryableError as exc:
                raise EmailSendError(detail=str(exc)) from exc
            except httpx.TransportError as exc:
                raise EmailSendError(detail=f"Transport error: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()


def _render_invite_html(*, invite_url: str) -> str:
    return (
        "<p>Hello,</p>"
        "<p>Your QuantBridge Beta invitation is ready. Click the link below to accept:</p>"
        f'<p><a href="{invite_url}">{invite_url}</a></p>'
        "<p>This link expires in 7 days.</p>"
        "<p>— QuantBridge team</p>"
    )


def _render_invite_text(*, invite_url: str) -> str:
    return (
        "Hello,\n\n"
        f"Your QuantBridge Beta invitation is ready: {invite_url}\n\n"
        "This link expires in 7 days.\n\n"
        "— QuantBridge team\n"
    )

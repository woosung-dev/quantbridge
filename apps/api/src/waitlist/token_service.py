"""HMAC-SHA256 signed JSON invite token.

구조: `{b64url(payload_json)}.{b64url(signature)}`
payload: `{"email": "...", "nonce": "...", "exp": <unix_ts>}`

- base64url (no padding) encode 로 URL-safe.
- signature: HMAC-SHA256(secret, payload_bytes).
- 만료: 발급 시점 + 7 일. 검증 시 현재 시각 비교.
- 변조 감지: hmac.compare_digest 로 timing-safe 비교.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from src.waitlist.exceptions import (
    InviteTokenExpiredError,
    InviteTokenInvalidError,
)

DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 일


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(frozen=True)
class InviteTokenPayload:
    email: str
    nonce: str
    exp: int  # unix seconds


class InviteTokenService:
    """HMAC-SHA256 서명된 JSON token 발행/검증."""

    def __init__(self, secret: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        if not secret or len(secret) < 16:
            raise ValueError(
                "WAITLIST_TOKEN_SECRET must be at least 16 characters"
            )
        self._secret = secret.encode("utf-8")
        self._ttl = ttl_seconds

    def issue(self, email: str, *, now: int | None = None) -> str:
        ts = int(time.time()) if now is None else now
        payload = InviteTokenPayload(
            email=email.strip().lower(),
            nonce=secrets.token_urlsafe(16),
            exp=ts + self._ttl,
        )
        payload_json = json.dumps(
            {"email": payload.email, "nonce": payload.nonce, "exp": payload.exp},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(self._secret, payload_json, hashlib.sha256).digest()
        return f"{_b64url_encode(payload_json)}.{_b64url_encode(signature)}"

    def verify(self, token: str, *, now: int | None = None) -> InviteTokenPayload:
        """Raises InviteTokenInvalidError / InviteTokenExpiredError."""
        try:
            payload_part, signature_part = token.split(".", 1)
        except ValueError as exc:  # token 구조 오류
            raise InviteTokenInvalidError() from exc

        try:
            payload_bytes = _b64url_decode(payload_part)
            signature_bytes = _b64url_decode(signature_part)
        except (ValueError, TypeError) as exc:
            raise InviteTokenInvalidError() from exc

        expected = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, signature_bytes):
            raise InviteTokenInvalidError()

        try:
            decoded = json.loads(payload_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InviteTokenInvalidError() from exc

        email = decoded.get("email")
        nonce = decoded.get("nonce")
        exp = decoded.get("exp")
        if not isinstance(email, str) or not isinstance(nonce, str) or not isinstance(exp, int):
            raise InviteTokenInvalidError()

        current = int(time.time()) if now is None else now
        if current >= exp:
            raise InviteTokenExpiredError()

        return InviteTokenPayload(email=email, nonce=nonce, exp=exp)

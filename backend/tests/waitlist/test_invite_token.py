"""InviteTokenService — 3 TDD (roundtrip / expired / tampered)."""
from __future__ import annotations

import time

import pytest

from src.waitlist.exceptions import (
    InviteTokenExpiredError,
    InviteTokenInvalidError,
)
from src.waitlist.token_service import InviteTokenService


def test_token_roundtrip_returns_same_email() -> None:
    svc = InviteTokenService(secret="a" * 32, ttl_seconds=60)
    token = svc.issue("user@example.com")
    payload = svc.verify(token)
    assert payload.email == "user@example.com"
    assert payload.nonce  # 비어있지 않음
    assert payload.exp > int(time.time())


def test_token_expired_raises() -> None:
    svc = InviteTokenService(secret="a" * 32, ttl_seconds=10)
    now = int(time.time())
    token = svc.issue("user@example.com", now=now)
    # 검증 시점을 TTL + 1 초 뒤로 시뮬레이션
    with pytest.raises(InviteTokenExpiredError):
        svc.verify(token, now=now + 11)


def test_token_tampered_signature_raises() -> None:
    svc = InviteTokenService(secret="a" * 32, ttl_seconds=60)
    token = svc.issue("user@example.com")
    payload_part, _sig_part = token.split(".", 1)
    # 서명을 임의 base64url 문자열로 교체
    tampered = f"{payload_part}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    with pytest.raises(InviteTokenInvalidError):
        svc.verify(tampered)

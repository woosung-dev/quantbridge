"""JWT + JWKS 검증기 — 진짜 Ed25519 키로 서명해 양성 1건 + **음성 대조 5건**을 잰다(ADR-034).

★이 파일이 종전 `test_clerk_auth.py` 의 자리다. 그쪽은 Clerk SDK 를 `MagicMock` 으로 바꿔
`is_signed_in=False` 를 돌려주게 했다 — 즉 **우리가 정한 답을 우리가 다시 읽는** 시험이라
서명·만료·iss·aud 중 무엇도 실제로 검증되지 않았다. 여기서는 라이브러리에 실제 토큰을 먹인다.

★`PyJWKClient.fetch_data` 만 가로챈다. kid 매칭·캐시·디코드는 **진짜 경로**가 돈다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt import PyJWKClient
from jwt.utils import base64url_encode

ISSUER = "https://qb.test"
KID = "test-key-1"


def _keypair() -> tuple[Ed25519PrivateKey, dict[str, Any]]:
    """Ed25519 개인키와 그 공개키의 JWKS 표현을 만든다."""
    private = Ed25519PrivateKey.generate()
    raw_public = private.public_key().public_bytes_raw()
    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": base64url_encode(raw_public).decode(),
        "kid": KID,
        "alg": "EdDSA",
        "use": "sig",
    }
    return private, {"keys": [jwk]}


def _sign(private: Ed25519PrivateKey, **overrides: Any) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": "better-auth-user-1",
        "iss": ISSUER,
        "aud": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "email": "user@example.com",
        "username": "tester",
    }
    payload.update(overrides)
    headers = {"kid": overrides.pop("_kid", KID)}
    return jwt.encode(payload, private, algorithm="EdDSA", headers=headers)


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch):
    """검증기를 이 테스트의 발급자·키셋에 맞춰 세운다."""
    from src.core.config import settings
    from src.realtime import auth as auth_module

    private, jwks = _keypair()
    monkeypatch.setattr(settings, "better_auth_url", ISSUER, raising=False)
    monkeypatch.setattr(settings, "better_auth_jwks_url", f"{ISSUER}/api/auth/jwks", raising=False)
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: json.loads(json.dumps(jwks)))
    auth_module.reset_jwks_cache()
    yield private, auth_module
    auth_module.reset_jwks_cache()


def _decode(auth_module, token: str) -> dict[str, Any]:
    return auth_module._decode(token)


def test_valid_token_decodes(auth_env) -> None:
    """양성 대조 — 제대로 서명된 토큰은 payload 를 낸다."""
    private, auth_module = auth_env
    payload = _decode(auth_module, _sign(private))
    assert payload["sub"] == "better-auth-user-1"
    assert payload["email"] == "user@example.com"


def test_forged_signature_is_rejected(auth_env) -> None:
    """음성 ① — 다른 키로 서명한 토큰은 통과하지 못한다."""
    _, auth_module = auth_env
    other, _ = _keypair()
    with pytest.raises(jwt.InvalidSignatureError):
        _decode(auth_module, _sign(other))


def test_expired_token_is_rejected(auth_env) -> None:
    """음성 ② — 만료."""
    private, auth_module = auth_env
    past = datetime.now(UTC) - timedelta(minutes=1)
    with pytest.raises(jwt.ExpiredSignatureError):
        _decode(auth_module, _sign(private, exp=int(past.timestamp())))


def test_issuer_mismatch_is_rejected(auth_env) -> None:
    """음성 ③ — 발급자 불일치. 다른 Better Auth 인스턴스의 토큰이 우리 API 를 열지 못한다."""
    private, auth_module = auth_env
    with pytest.raises(jwt.InvalidIssuerError):
        _decode(auth_module, _sign(private, iss="https://evil.test"))


def test_audience_mismatch_is_rejected(auth_env) -> None:
    """음성 ④ — 수신자 불일치."""
    private, auth_module = auth_env
    with pytest.raises(jwt.InvalidAudienceError):
        _decode(auth_module, _sign(private, aud="https://other.test"))


def test_unknown_kid_is_rejected(auth_env) -> None:
    """음성 ⑤ — 키셋에 없는 kid. 서명 자체는 유효해도 신뢰할 키가 아니다."""
    private, auth_module = auth_env
    token = jwt.encode(
        {
            "sub": "x",
            "iss": ISSUER,
            "aud": ISSUER,
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        private,
        algorithm="EdDSA",
        headers={"kid": "not-in-the-keyset"},
    )
    with pytest.raises(jwt.PyJWKClientError):
        _decode(auth_module, token)


def test_missing_required_claim_is_rejected(auth_env) -> None:
    """음성 ⑥ — `sub` 없는 토큰. 우리 사용자 매핑의 유일한 키라 없으면 통과시키면 안 된다."""
    private, auth_module = auth_env
    token = jwt.encode(
        {
            "iss": ISSUER,
            "aud": ISSUER,
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        private,
        algorithm="EdDSA",
        headers={"kid": KID},
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        _decode(auth_module, token)


@pytest.mark.asyncio
async def test_me_without_auth_header_returns_401(client) -> None:
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "auth_invalid_token"


@pytest.mark.asyncio
async def test_me_with_garbage_token_returns_401(client) -> None:
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "auth_invalid_token"


@pytest.mark.asyncio
async def test_me_with_non_bearer_scheme_returns_401(client) -> None:
    """`Basic` 등 다른 스킴을 Bearer 로 오인하지 않는다."""
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "auth_invalid_token"

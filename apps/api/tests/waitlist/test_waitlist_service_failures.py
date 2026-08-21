"""waitlist 초대 흐름의 실패 경로 회귀 테스트.

DB·Redis·외부 Resend 호출 없이 HMAC 검증, 메일 오류 변환, 서비스 조립의 경계를 고정한다.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Generator
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
import tenacity
from sqlalchemy.exc import IntegrityError

from src.waitlist.email_service import EmailService, _RetryableError, _send_once
from src.waitlist.exceptions import (
    DuplicateEmailError,
    EmailSendError,
    InviteTokenExpiredError,
    InviteTokenInvalidError,
    WaitlistNotFoundError,
)
from src.waitlist.models import WaitlistStatus
from src.waitlist.schemas import CreateWaitlistApplicationRequest
from src.waitlist.service import ServiceConfig, WaitlistService
from src.waitlist.token_service import InviteTokenPayload, InviteTokenService

TOKEN_SECRET = "waitlist-test-secret-0123456789"
OTHER_TOKEN_SECRET = "other-waitlist-test-secret-987654"


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Generator[None, None, None]:
    """상위 conftest의 Redis limiter reset을 이 순수 단위 테스트에서는 비활성화한다."""
    yield


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _signed_token(payload: bytes, *, secret: str = TOKEN_SECRET) -> str:
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"


def _make_request() -> CreateWaitlistApplicationRequest:
    return CreateWaitlistApplicationRequest(
        email="user@example.com",
        tv_subscription="pro",
        exchange_capital="1k_to_10k",
        pine_experience="beginner",
        existing_tool=None,
        pain_point="백테스트 결과를 더 빨리 검증하고 싶습니다.",
    )


def _make_waitlist_service(
    *,
    repo: AsyncMock,
    token_service: Mock | None = None,
) -> WaitlistService:
    return WaitlistService(
        repo=repo,
        email_service=AsyncMock(),
        token_service=token_service or Mock(),
        config=ServiceConfig(invite_base_url="https://app.example.com/invite"),
    )


def _disable_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    retrying = _send_once.retry  # type: ignore[attr-defined]
    monkeypatch.setattr(retrying, "wait", tenacity.wait_fixed(0))


@pytest.mark.parametrize("token", ["missing-separator", "A.A"])
def test_verify_rejects_malformed_tokens(token: str) -> None:
    service = InviteTokenService(secret=TOKEN_SECRET)

    with pytest.raises(InviteTokenInvalidError):
        service.verify(token, now=1_000)


def test_verify_rejects_signed_non_json_payload() -> None:
    service = InviteTokenService(secret=TOKEN_SECRET)
    token = _signed_token(b"not-json")

    with pytest.raises(InviteTokenInvalidError):
        service.verify(token, now=1_000)


def test_verify_rejects_signed_payload_with_string_exp() -> None:
    service = InviteTokenService(secret=TOKEN_SECRET)
    payload = json.dumps(
        {"email": "user@example.com", "nonce": "nonce", "exp": "1060"},
        separators=(",", ":"),
    ).encode("utf-8")
    token = _signed_token(payload)

    with pytest.raises(InviteTokenInvalidError):
        service.verify(token, now=1_000)


def test_verify_rejects_token_signed_by_other_secret() -> None:
    signer = InviteTokenService(secret=OTHER_TOKEN_SECRET, ttl_seconds=60)
    verifier = InviteTokenService(secret=TOKEN_SECRET, ttl_seconds=60)
    token = signer.issue("user@example.com", now=1_000)

    with pytest.raises(InviteTokenInvalidError):
        verifier.verify(token, now=1_001)


def test_verify_expiry_boundary_distinguishes_valid_and_expired() -> None:
    service = InviteTokenService(secret=TOKEN_SECRET, ttl_seconds=60)
    token = service.issue("user@example.com", now=1_000)
    payload = service.verify(token, now=1_059)

    assert payload.exp == 1_060
    with pytest.raises(InviteTokenExpiredError):
        service.verify(token, now=1_060)


def test_issue_and_verify_normalize_email() -> None:
    service = InviteTokenService(secret=TOKEN_SECRET, ttl_seconds=60)
    token = service.issue("  USER@Example.COM  ", now=1_000)

    payload = service.verify(token, now=1_001)

    assert payload.email == "user@example.com"


@pytest.mark.parametrize("secret", ["a" * 15, ""])
def test_invite_token_service_rejects_short_or_empty_secret(secret: str) -> None:
    with pytest.raises(
        ValueError,
        match="WAITLIST_TOKEN_SECRET must be at least 16 characters",
    ):
        InviteTokenService(secret=secret)


@pytest.mark.asyncio
async def test_send_once_converts_permanent_4xx_to_email_send_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="invalid recipient")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EmailSendError) as exc_info:
            await _send_once(client, api_key="test-key", payload={})

    assert exc_info.value.detail == "Resend rejected email: 400"


@pytest.mark.asyncio
async def test_send_once_uses_retryable_error_for_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_retry_wait(monkeypatch)
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="throttled")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(_RetryableError, match="Resend 429: throttled"):
            await _send_once(client, api_key="test-key", payload={})

    assert attempts == 3


@pytest.mark.asyncio
async def test_send_invite_email_converts_retryable_and_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_retry_wait(monkeypatch)

    def retryable_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="throttled")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(retryable_handler)
    ) as retryable_client:
        retryable_service = EmailService(api_key="test-key", client=retryable_client)
        with pytest.raises(EmailSendError) as retryable_exc:
            await retryable_service.send_invite_email(
                to_email="user@example.com",
                invite_url="https://app.example.com/invite/token",
            )

    assert retryable_exc.value.detail == "Resend 429: throttled"
    assert isinstance(retryable_exc.value.__cause__, _RetryableError)

    def transport_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection reset", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport_handler)
    ) as transport_client:
        transport_service = EmailService(api_key="test-key", client=transport_client)
        with pytest.raises(EmailSendError) as transport_exc:
            await transport_service.send_invite_email(
                to_email="user@example.com",
                invite_url="https://app.example.com/invite/token",
            )

    assert transport_exc.value.detail == "Transport error: connection reset"
    assert isinstance(transport_exc.value.__cause__, httpx.ConnectError)


@pytest.mark.asyncio
async def test_email_service_owned_client_closes_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.waitlist import email_service as email_service_module

    actual_async_client = httpx.AsyncClient
    created_clients: list[httpx.AsyncClient] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="invalid recipient")

    def client_factory() -> httpx.AsyncClient:
        client = actual_async_client(transport=httpx.MockTransport(handler))
        close_spy = AsyncMock(wraps=client.aclose)
        monkeypatch.setattr(client, "aclose", close_spy)
        created_clients.append(client)
        return client

    monkeypatch.setattr(email_service_module.httpx, "AsyncClient", client_factory)
    service = EmailService(api_key="test-key")

    with pytest.raises(EmailSendError):
        await service.send_invite_email(
            to_email="user@example.com",
            invite_url="https://app.example.com/invite/token",
        )

    assert len(created_clients) == 1
    created_clients[0].aclose.assert_awaited_once()  # type: ignore[attr-defined]
    assert created_clients[0].is_closed


@pytest.mark.asyncio
async def test_email_service_does_not_close_injected_client() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "email_123"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = EmailService(api_key="test-key", client=client)
        await service.send_invite_email(
            to_email="user@example.com",
            invite_url="https://app.example.com/invite/token",
        )

        assert not client.is_closed


def test_email_service_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError, match="Resend API key is empty"):
        EmailService(api_key="")


@pytest.mark.asyncio
@pytest.mark.parametrize("failing_method", ["create", "commit"])
async def test_submit_application_rolls_back_integrity_error(
    failing_method: str,
) -> None:
    repo = AsyncMock()
    repo.find_by_email = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=object())
    repo.commit = AsyncMock()
    error = IntegrityError("INSERT INTO waitlist", {}, Exception("duplicate email"))
    getattr(repo, failing_method).side_effect = error
    service = _make_waitlist_service(repo=repo)

    with pytest.raises(DuplicateEmailError) as exc_info:
        await service.submit_application(_make_request())

    assert exc_info.value.__cause__ is error
    repo.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_invite_token_requires_existing_waitlist_application() -> None:
    token_service = Mock()
    token_service.verify.return_value = InviteTokenPayload(
        email="user@example.com",
        nonce="nonce",
        exp=2_000,
    )
    repo = AsyncMock()
    repo.find_by_invite_token = AsyncMock(return_value=None)
    service = _make_waitlist_service(repo=repo, token_service=token_service)

    with pytest.raises(WaitlistNotFoundError):
        await service.verify_invite_token("valid-token")

    token_service.verify.assert_called_once_with("valid-token")
    repo.find_by_invite_token.assert_awaited_once_with("valid-token")


@pytest.mark.asyncio
async def test_verify_invite_token_validates_before_database_lookup() -> None:
    token_service = Mock()
    token_service.verify.side_effect = InviteTokenInvalidError()
    repo = AsyncMock()
    repo.find_by_invite_token = AsyncMock()
    service = _make_waitlist_service(repo=repo, token_service=token_service)

    with pytest.raises(InviteTokenInvalidError):
        await service.verify_invite_token("invalid-token")

    token_service.verify.assert_called_once_with("invalid-token")
    repo.find_by_invite_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_list_delegates_status_pagination_and_total() -> None:
    repo = AsyncMock()
    repo.list_by_status = AsyncMock(return_value=([], 0))
    service = _make_waitlist_service(repo=repo)

    response = await service.admin_list(
        status=WaitlistStatus.pending,
        limit=20,
        offset=40,
    )

    assert response.items == []
    assert response.total == 0
    repo.list_by_status.assert_awaited_once_with(
        status=WaitlistStatus.pending,
        limit=20,
        offset=40,
    )

"""EmailService Resend wrapper — 2 TDD (성공 / 500 retry 성공).

tenacity retry 를 실제 sleep 없이 확인하기 위해 wait 를 0 초로 monkeypatch.
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from src.waitlist.email_service import EmailService


class _CallCounter:
    """MockTransport call count tracker."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:  # pragma: no cover - trivial
        raise NotImplementedError


def _fast_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """tenacity wait 제거 — 테스트 latency 단축."""
    import tenacity

    # _send_once 함수 객체의 retry wait 를 fixed 0 으로 교체.
    # tenacity 는 함수에 `retry` attribute 로 Retrying 객체를 부착.
    from src.waitlist import email_service as es_module

    retrying = es_module._send_once.retry  # type: ignore[attr-defined]
    retrying.wait = tenacity.wait_fixed(0)


@pytest.mark.asyncio
async def test_send_invite_email_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _fast_retry(monkeypatch)

    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={"id": "email_123"},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    svc = EmailService(api_key="test-key", client=client)

    await svc.send_invite_email(
        to_email="alice@example.com",
        invite_url="https://app.example.com/invite/TOKEN",
    )

    assert seen["url"] == "https://api.resend.com/emails"
    assert seen["auth"] == "Bearer test-key"
    await client.aclose()


@pytest.mark.asyncio
async def test_send_invite_email_500_retry_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fast_retry(monkeypatch)
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        if counter["n"] < 3:
            return httpx.Response(500, text="upstream error")
        return httpx.Response(200, json={"id": "email_ok"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    svc = EmailService(api_key="test-key", client=client)

    await svc.send_invite_email(
        to_email="alice@example.com",
        invite_url="https://app.example.com/invite/TOKEN",
    )

    assert counter["n"] == 3
    await client.aclose()

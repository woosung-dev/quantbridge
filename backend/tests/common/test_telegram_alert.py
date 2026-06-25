"""Wave 0 W2 — TelegramAlertService TDD (SlackAlertService 미러).

`tests/common/test_alert.py` 의 httpx.MockTransport 패턴을 미러한다.
- per-call httpx client (test 에서는 inject)
- token/chat_id 미설정 → silent skip
- 503 retry once / 4xx 즉시 fail
- BoundedSemaphore(8) max_in_flight 패턴 (wall-clock timing 회피)
- 15s timeout
"""
from __future__ import annotations

import asyncio
import contextlib
import json as _json
from typing import Any

import httpx
import pytest

from src.common.telegram_alert import (
    TelegramAlertService,
    send_telegram_critical_alert,
)
from src.core.config import Settings

_BOT_TOKEN = "123456789:AAH-DummyTokenForTestsOnly_xxxxxxxxxxxx"
_CHAT_ID = "987654321"


@pytest.fixture
def settings_with_telegram(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Telegram bot token + chat id 설정된 Settings."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", _BOT_TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", _CHAT_ID)
    return Settings()


@pytest.fixture
def settings_without_telegram(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Telegram 미설정 Settings."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    return Settings()


@pytest.fixture
def settings_token_no_chat(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """token 만 있고 chat_id 누락 — silent skip 대상."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", _BOT_TOKEN)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    return Settings()


def _make_mock_client(
    handler: Any, *, transport_kwargs: dict[str, Any] | None = None
) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, **(transport_kwargs or {}))


@pytest.mark.asyncio
async def test_send_success_with_telegram_configured(
    settings_with_telegram: Settings,
) -> None:
    """token+chat 설정 시 200 → True + payload(chat_id/text/severity emoji) 검증."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    async with _make_mock_client(handler) as client:
        service = TelegramAlertService(settings_with_telegram, client=client)
        result = await service.send(
            "critical", "KS triggered", "MDD 30%", {"strategy_id": "abc-123"}
        )

    assert result is True
    assert len(captured) == 1
    # 엔드포인트에 bot token 포함
    assert captured[0].url.path == f"/bot{_BOT_TOKEN}/sendMessage"
    payload = _json.loads(captured[0].read())
    assert payload["chat_id"] == _CHAT_ID
    text = payload["text"]
    assert "🔴" in text  # critical emoji
    assert "[critical] KS triggered" in text
    assert "MDD 30%" in text
    assert "strategy_id" in text and "abc-123" in text


@pytest.mark.asyncio
async def test_send_silent_skip_when_token_unset(
    settings_without_telegram: Settings,
) -> None:
    """token/chat 미설정 시 raise 없이 False 반환."""
    service = TelegramAlertService(settings_without_telegram)
    result = await service.send("warning", "test", "msg", None)
    assert result is False


@pytest.mark.asyncio
async def test_send_silent_skip_when_chat_id_missing(
    settings_token_no_chat: Settings,
) -> None:
    """token 만 있고 chat_id 누락 시 silent skip (False)."""
    service = TelegramAlertService(settings_token_no_chat)
    result = await service.send("critical", "t", "m", None)
    assert result is False


@pytest.mark.asyncio
async def test_send_retries_once_on_503(settings_with_telegram: Settings) -> None:
    """503 → retry → 200 = 총 2회 호출 + True."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, json={"error": "throttled"})
        return httpx.Response(200, json={"ok": True})

    async with _make_mock_client(handler) as client:
        service = TelegramAlertService(settings_with_telegram, client=client)
        result = await service.send("critical", "t", "m", None)

    assert result is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_send_returns_false_on_persistent_4xx(
    settings_with_telegram: Settings,
) -> None:
    """4xx 는 retry 대상 아님 → 1회 후 즉시 fail → False (raise 차단)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "chat not found"})

    async with _make_mock_client(handler) as client:
        service = TelegramAlertService(settings_with_telegram, client=client)
        result = await service.send("critical", "t", "m", None)
    assert result is False


@pytest.mark.asyncio
async def test_send_returns_false_on_persistent_503(
    settings_with_telegram: Settings,
) -> None:
    """503 이 retry 후에도 지속 → RetryError catch → False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "throttled"})

    async with _make_mock_client(handler) as client:
        service = TelegramAlertService(settings_with_telegram, client=client)
        result = await service.send("critical", "t", "m", None)
    assert result is False


@pytest.mark.asyncio
async def test_bounded_semaphore_caps_concurrent_sends_at_8(
    settings_with_telegram: Settings,
) -> None:
    """max_in_flight counter 패턴 — 12 동시 send 시 in-flight 가 8 초과 금지."""
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    release_event = asyncio.Event()

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(release_event.wait(), timeout=2.0)
        async with lock:
            in_flight -= 1
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(slow_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = TelegramAlertService(settings_with_telegram, client=client)
        tasks = [
            asyncio.create_task(service.send("info", f"t{i}", "m", None))
            for i in range(12)
        ]
        await asyncio.sleep(0.1)
        release_event.set()
        results = await asyncio.gather(*tasks)

    assert all(results)
    assert max_in_flight <= 8, f"max_in_flight={max_in_flight} exceeded Semaphore(8)"


@pytest.mark.asyncio
async def test_send_telegram_critical_alert_convenience(
    settings_with_telegram: Settings,
) -> None:
    """helper — 'critical' severity 자동 + client 주입."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200)

    async with _make_mock_client(handler) as client:
        result = await send_telegram_critical_alert(
            settings_with_telegram, "t", "m", None, client=client
        )

    assert result is True
    text = _json.loads(captured[0].read())["text"]
    assert text.startswith("🔴")
    assert "[critical]" in text


@pytest.mark.asyncio
async def test_severity_emoji_mapping(settings_with_telegram: Settings) -> None:
    """severity → emoji prefix 매핑 (critical/warning/info)."""
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(_json.loads(request.read())["text"])
        return httpx.Response(200)

    async with _make_mock_client(handler) as client:
        service = TelegramAlertService(settings_with_telegram, client=client)
        await service.send("warning", "w", "m", None)
        await service.send("info", "i", "m", None)

    assert captured[0].startswith("🟠")  # warning
    assert captured[1].startswith("🟢")  # info

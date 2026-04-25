"""Sprint 12 Phase A — SlackAlertService TDD.

codex G0/G1 결정 반영:
- per-call httpx client (test 에서는 inject)
- BoundedSemaphore(8) max_in_flight pattern (codex G1 #9 — wall-clock timing 회피)
- silent skip on missing webhook
- 503 retry once
- best-effort policy — _PENDING_ALERTS module-level set 으로 task 보존
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import httpx
import pytest

from src.common.alert import SlackAlertService, _cap_context, send_critical_alert
from src.core.config import Settings


@pytest.fixture
def settings_with_slack(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Slack webhook 설정된 Settings."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/X")
    return Settings()


@pytest.fixture
def settings_without_slack(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Slack webhook 미설정 Settings."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    return Settings()


def _make_mock_client(handler: Any, *, transport_kwargs: dict[str, Any] | None = None) -> httpx.AsyncClient:
    """httpx.MockTransport 로 wrapping 한 AsyncClient."""
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, **(transport_kwargs or {}))


@pytest.mark.asyncio
async def test_send_success_with_webhook_configured(settings_with_slack: Settings) -> None:
    """webhook 설정 시 200 → True 반환 + payload 형태 검증."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    async with _make_mock_client(handler) as client:
        service = SlackAlertService(settings_with_slack, client=client)
        result = await service.send(
            "critical", "KS triggered", "MDD 30%", {"strategy_id": "abc-123"}
        )

    assert result is True
    assert len(captured) == 1
    body = captured[0].read()
    import json as _json

    payload = _json.loads(body)
    assert payload["text"] == "[critical] KS triggered"
    assert payload["attachments"][0]["color"] == "#FF0000"
    assert payload["attachments"][0]["text"] == "MDD 30%"
    assert payload["attachments"][0]["fields"][0]["title"] == "strategy_id"
    assert payload["attachments"][0]["fields"][0]["value"] == "abc-123"


@pytest.mark.asyncio
async def test_send_silent_skip_when_webhook_unset(settings_without_slack: Settings) -> None:
    """webhook 미설정 시 raise 없이 False 반환."""
    service = SlackAlertService(settings_without_slack)
    result = await service.send("warning", "test", "msg", None)
    assert result is False


@pytest.mark.asyncio
async def test_send_retries_once_on_503(settings_with_slack: Settings) -> None:
    """503 → retry → 200 = 총 2회 호출 + True 반환."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, json={"error": "throttled"})
        return httpx.Response(200, json={"ok": True})

    async with _make_mock_client(handler) as client:
        service = SlackAlertService(settings_with_slack, client=client)
        result = await service.send("critical", "t", "m", None)

    assert result is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_bounded_semaphore_caps_concurrent_sends_at_8(
    settings_with_slack: Settings,
) -> None:
    """codex G1 #9 — wall-clock 대신 max_in_flight counter 패턴.

    12 동시 send 시 in-flight 가 절대 8 을 넘지 않아야 함.
    """
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    release_event = asyncio.Event()

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        # 모든 task 가 동시 진입할 시간 확보
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(release_event.wait(), timeout=2.0)
        async with lock:
            in_flight -= 1
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(slow_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = SlackAlertService(settings_with_slack, client=client)

        # 12 동시 send
        tasks = [
            asyncio.create_task(service.send("info", f"t{i}", "m", None))
            for i in range(12)
        ]
        # 모두 in-flight 또는 semaphore 대기 상태가 되도록 잠시 대기
        await asyncio.sleep(0.1)
        # 그 후 release → 8 동시 → 다음 4 → 종료
        release_event.set()
        results = await asyncio.gather(*tasks)

    assert all(results)
    assert max_in_flight <= 8, f"max_in_flight={max_in_flight} exceeded BoundedSemaphore(8)"


@pytest.mark.asyncio
async def test_send_critical_alert_convenience(settings_with_slack: Settings) -> None:
    """send_critical_alert helper — 'critical' severity 자동 + client 주입."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200)

    async with _make_mock_client(handler) as client:
        result = await send_critical_alert(
            settings_with_slack, "t", "m", None, client=client
        )

    assert result is True
    body = captured[0].read()
    import json as _json

    assert _json.loads(body)["text"].startswith("[critical]")


def test_cap_context_truncates_oversize() -> None:
    """G1 #7 — 20 keys + 500 chars/value cap."""
    big_ctx = {f"k{i}": "x" * 600 for i in range(30)}
    capped = _cap_context(big_ctx, max_keys=20, max_value_len=500)
    assert len(capped) <= 21  # 20 keys + _truncated marker
    assert "_truncated" in capped
    assert capped["_truncated"] == "10 more keys omitted"
    # 첫 번째 value 가 500 + ellipsis
    first_val = capped["k0"]
    assert len(first_val) <= 501  # 500 + …
    assert first_val.endswith("…")


def test_cap_context_handles_none() -> None:
    """None / 빈 dict 모두 안전."""
    assert _cap_context(None) == {}
    assert _cap_context({}) == {}

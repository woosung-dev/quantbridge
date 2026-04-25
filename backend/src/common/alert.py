"""Slack incoming webhook alert sender (Sprint 12 Phase A).

**Best-effort policy** (codex G1 #6 결정):
fire-and-forget 발송 task 는 module-level ``_PENDING_ALERTS`` set 이 strong ref
로 보존하지만, FastAPI lifespan / Celery worker_shutdown 에 drain wire-up 이
연결되어 있지 않다. 정상 종료 / 배포 재시작 중 in-flight alert 가 drop 될 수
있다. KS 발동은 드물고 Slack POST 는 ms 단위라 실제 drop 위험은 낮다.

향후 (Sprint 13+) lifespan-owned singleton AlertDispatcher 로 이관하며 drain
을 wire-up. 그때까지 본 모듈은 best-effort.

설계 원칙:
- per-call ``httpx.AsyncClient`` (``email_service.py`` 의 ``owns_client`` 패턴):
  Celery prefork + asyncio.run() loop 변경 양쪽에서 fork-safe.
- module-level ``BoundedSemaphore(8)``: burst 시 fan-in 방지. 동시 Nxworker
  프로세스에 대해 worker 별 8 이 상한.
- ``asyncio.wait_for(timeout=15s)``: Slack stuck 방지.
- ``_cap_context``: payload size 보호 (40k Slack 한도 → 20 keys x 500 chars cap).
- ``slack_webhook_url is None`` → silent skip. raise X.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from src.core.config import Settings

logger = logging.getLogger(__name__)

Severity = Literal["critical", "warning", "info"]
_COLOR: dict[Severity, str] = {
    "critical": "#FF0000",
    "warning": "#FFA500",
    "info": "#00CC00",
}

# 동시 send burst 상한 — worker 프로세스별 8.
_SEND_SEMAPHORE = asyncio.Semaphore(8)
_SEND_TIMEOUT_S = 15.0

# fire-and-forget task strong-ref. Service GC 후에도 task 보존 (asyncio loop 가
# weak-ref 만 유지하는 함정 방어). best-effort — shutdown 시 drop 가능.
_PENDING_ALERTS: set[asyncio.Task[Any]] = set()


def _cap_context(
    ctx: dict[str, Any] | None,
    *,
    max_keys: int = 20,
    max_value_len: int = 500,
) -> dict[str, str]:
    """Slack 40k payload 한도 방어 (codex G1 #7).

    20 keys 초과 시 ``_truncated`` marker. value 500 chars 초과 시 ``…`` 절단.
    """
    if not ctx:
        return {}
    capped: dict[str, str] = {}
    items = list(ctx.items())
    for i, (k, v) in enumerate(items):
        if i >= max_keys:
            capped["_truncated"] = f"{len(items) - max_keys} more keys omitted"
            break
        s = str(v)
        capped[str(k)] = s if len(s) <= max_value_len else s[:max_value_len] + "…"
    return capped


class SlackAlertService:
    """Slack incoming webhook 발송 service.

    test 시 ``client`` 주입 가능. 운영에서는 None → per-call client 생성/close.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client

    async def send(
        self,
        severity: Severity,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Slack 메시지 발송.

        Returns True on 2xx (retry 1회 후 성공 포함), False on:
        - webhook URL 미설정 (silent skip)
        - 15s timeout
        - retry 후에도 실패
        """
        webhook = self._settings.slack_webhook_url
        if webhook is None:
            return False
        url = webhook.get_secret_value()
        if not url:  # 빈 문자열 안전망
            return False

        capped_ctx = _cap_context(context)
        payload: dict[str, Any] = {
            "text": f"[{severity}] {title}",
            "attachments": [
                {
                    "color": _COLOR[severity],
                    "text": message,
                    "fields": [
                        {"title": k, "value": v, "short": True} for k, v in capped_ctx.items()
                    ],
                }
            ],
        }

        async with _SEND_SEMAPHORE:
            try:
                return await asyncio.wait_for(
                    self._send_inner(url, payload), timeout=_SEND_TIMEOUT_S
                )
            except TimeoutError:
                logger.warning("slack_alert_timeout severity=%s title=%s", severity, title)
                return False
            except RetryError as exc:
                logger.warning("slack_alert_failed severity=%s err=%s", severity, exc)
                return False

    async def _send_inner(self, url: str, payload: dict[str, Any]) -> bool:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(5.0))
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(2),
                wait=wait_fixed(1),
                retry=retry_if_exception_type(httpx.HTTPError),
                reraise=True,
            ):
                with attempt:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 503:
                        # tenacity 가 503 도 재시도하도록 HTTPError 로 raise
                        raise httpx.HTTPError("503 Service Unavailable")
                    resp.raise_for_status()
                    return True
            return False  # unreachable (AsyncRetrying 가 성공/예외 둘 중 하나로 종료)
        finally:
            if owns_client:
                try:
                    await client.aclose()
                except Exception as exc:
                    logger.debug("slack_alert_aclose_failed err=%s", exc)


async def send_critical_alert(
    settings: Settings,
    title: str,
    message: str,
    context: dict[str, Any] | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """편의 함수 — severity='critical' 고정 + client 주입 가능 (test 용)."""
    return await SlackAlertService(settings, client=client).send(
        "critical", title, message, context
    )

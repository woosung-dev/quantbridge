"""Telegram Bot API critical-alert sender (Wave 0 W2 — SlackAlertService 미러).

`common/alert.py` 의 `SlackAlertService` 와 동일한 설계·시그니처를 미러한다:
- per-call ``httpx.AsyncClient`` (test 시 inject) — Celery prefork + loop 변경 fork-safe.
- module-level ``Semaphore(8)``: burst 시 fan-in 방지 (worker 별 8 상한).
- ``asyncio.wait_for(timeout=15s)``: API stuck 방지.
- ``_cap_context``: payload 보호 (alert.py 의 helper 재사용 — 중복 정의 회피).
- token / chat_id 미설정 → silent skip(False). raise X.

Slack 과 차이:
- Telegram Bot API ``sendMessage`` (chat_id + text). 색 필드가 없으므로 severity 는
  텍스트 prefix 이모지(🔴/🟠/🟢)로 표기.
- best-effort 정책 동일 — fan-out(Slack+Telegram 동시) 배선은 본 모듈 책임 아님
  (Orchestrator 후처리).
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

from src.common.alert import _cap_context
from src.core.config import Settings

logger = logging.getLogger(__name__)

Severity = Literal["critical", "warning", "info"]
# Slack 의 _COLOR 미러 — Telegram 은 색 필드 부재라 텍스트 prefix 이모지로 표기.
_EMOJI: dict[Severity, str] = {
    "critical": "🔴",
    "warning": "🟠",
    "info": "🟢",
}

_TELEGRAM_API_BASE = "https://api.telegram.org"

# 동시 send burst 상한 — worker 프로세스별 8 (alert.py 의 _SEND_SEMAPHORE 와 별도 인스턴스).
_SEND_SEMAPHORE = asyncio.Semaphore(8)
_SEND_TIMEOUT_S = 15.0


def _format_text(
    severity: Severity,
    title: str,
    message: str,
    context: dict[str, str],
) -> str:
    """severity 이모지 + 제목 + 본문 + context k:v 를 plain text 로 조립."""
    lines = [f"{_EMOJI[severity]} [{severity}] {title}", message]
    lines.extend(f"{k}: {v}" for k, v in context.items())
    return "\n".join(lines)


class TelegramAlertService:
    """Telegram Bot API ``sendMessage`` 발송 service.

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
        """Telegram 메시지 발송.

        Returns True on 2xx (retry 1회 후 성공 포함), False on:
        - bot token / chat_id 미설정 (silent skip)
        - 15s timeout
        - retry 후에도 실패
        """
        token_secret = self._settings.telegram_bot_token
        chat_id = self._settings.telegram_chat_id
        if token_secret is None or not chat_id:
            return False
        token = token_secret.get_secret_value()
        if not token:  # 빈 문자열 안전망
            return False

        url = f"{_TELEGRAM_API_BASE}/bot{token}/sendMessage"
        capped_ctx = _cap_context(context)
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": _format_text(severity, title, message, capped_ctx),
        }

        # alert.py 미러: wait_for 를 semaphore 밖에 두어 9번째 alert 가 timeout 을
        # 누적하지 않도록 (semaphore acquire + send) 전체가 _SEND_TIMEOUT_S 한도.
        try:
            return await asyncio.wait_for(
                self._send_with_semaphore(url, payload), timeout=_SEND_TIMEOUT_S
            )
        except TimeoutError:
            logger.warning("telegram_alert_timeout severity=%s title=%s", severity, title)
            return False
        except RetryError as exc:
            logger.warning("telegram_alert_failed_retry severity=%s err=%s", severity, exc)
            return False
        except httpx.HTTPError as exc:
            # tenacity reraise=True 시 마지막 HTTPError 전파 → "False 반환" 계약 유지.
            logger.warning("telegram_alert_failed_http severity=%s err=%s", severity, exc)
            return False

    async def _send_with_semaphore(self, url: str, payload: dict[str, Any]) -> bool:
        """semaphore acquire + send_inner 묶음 (wait_for 의 cancel 대상)."""
        async with _SEND_SEMAPHORE:
            return await self._send_inner(url, payload)

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
                        raise httpx.HTTPError("503 Service Unavailable")
                    resp.raise_for_status()
                    return True
            return False  # unreachable
        finally:
            if owns_client:
                try:
                    await client.aclose()
                except Exception as exc:
                    logger.debug("telegram_alert_aclose_failed err=%s", exc)


async def send_telegram_critical_alert(
    settings: Settings,
    title: str,
    message: str,
    context: dict[str, Any] | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """편의 함수 — severity='critical' 고정 + client 주입 가능 (test 용)."""
    return await TelegramAlertService(settings, client=client).send(
        "critical", title, message, context
    )

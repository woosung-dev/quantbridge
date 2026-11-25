"""익명 경로 IP 단위 rate limit — `/healthz` · `/api/v1/waitlist` (10초 30회 초과 → 429).

★왜 앱에 두나 (2026-11-20): Cloudflare 존(`woosung.dev`)이 Free 플랜이라 rate limiting 규칙이
**1개**뿐이고, 그 자리는 truewords 규칙이 쓰고 있다(1/1). 사용자 결정으로 그 규칙을 지우지
않고 같은 기준을 앱으로 옮긴다 — Cloudflare 규칙안과 같은 경로·같은 수치·IP 단위.

★slowapi 데코레이터로 안 하는 이유
- `/healthz` 는 slowapi 에서 **면제**다(헬스체크 스크래퍼). 면제를 풀면 기본 100/분이 같이 걸린다.
- slowapi 키는 JWT `sub` 를 먼저 본다. 이 규칙은 **IP 단위**여야 한다(익명 경로라서).
- 경로 **정확히 일치**·메서드 무관이라는 규칙 모양을 그대로 옮기기에 미들웨어가 맞다.

★웹훅(`/api/v1/webhooks/*`)은 넣지 않는다 — TradingView 가 소수의 공유 IP 로 보내므로 IP 단위
한도는 정상 알림을 막는다. 웹훅은 HMAC 이 1차 방어다.

IP 판정은 slowapi 와 같은 `client_ip_or_xff` 를 쓴다 — `TRUSTED_PROXIES` 안에서 온 요청만
`CF-Connecting-IP` 를 믿는다. 저장소도 같은 `REDIS_LOCK_URL`(DB 3)이고 키 접두사로 갈린다.
Redis 장애 시 slowapi 와 같이 **fail-open**(통과 + WARN).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import cast

import anyio.to_thread
from limits import RateLimitItem, parse
from limits.storage import Storage, storage_from_string
from limits.strategies import FixedWindowRateLimiter
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.common.metrics import qb_rate_limit_throttled_total
from src.common.metrics_multiproc import record_metric_safely
from src.common.rate_limit import client_ip_or_xff
from src.core.config import secret_value, settings

_LOGGER = logging.getLogger(__name__)

ANON_LIMITED_PATHS: frozenset[str] = frozenset({"/healthz", "/api/v1/waitlist"})
ANON_PATH_LIMIT: RateLimitItem = parse("30 per 10 seconds")
_RETRY_AFTER_S = "10"
_KEY_NAMESPACE = "anon_path"


@lru_cache(maxsize=1)
def _storage() -> Storage:
    """저장소는 첫 사용 때 만든다 — import 시점에 Redis 에 붙지 않는다(slowapi 와 같은 원칙)."""
    # 동기 URI(`redis://`·`memory://`)만 온다 — `async+` 접두사는 설정하지 않는다.
    return cast(
        Storage,
        storage_from_string(
            secret_value(settings.redis_lock_url),
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
            retry_on_timeout=False,
        ),
    )


def _limiter() -> FixedWindowRateLimiter:
    return FixedWindowRateLimiter(_storage())


def _hit(path: str, ip: str) -> bool:
    """한도 안이면 True. 저장소 오류는 호출부가 잡는다."""
    return _limiter().hit(ANON_PATH_LIMIT, _KEY_NAMESPACE, path, ip)


class AnonPathRateLimitMiddleware:
    """`ANON_LIMITED_PATHS` 에 정확히 일치하는 HTTP 요청만 IP 단위로 센다."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in ANON_LIMITED_PATHS:
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        ip = client_ip_or_xff(Request(scope))
        try:
            allowed = await anyio.to_thread.run_sync(_hit, path, ip)
        except Exception:  # fail-open 이 계약이다
            _LOGGER.warning("anon_path_rate_limit_storage_error", extra={"path": path})
            allowed = True

        if allowed:
            await self.app(scope, receive, send)
            return

        record_metric_safely(
            lambda: qb_rate_limit_throttled_total.labels(scope="ip", endpoint=path).inc()
        )
        response = JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "code": "rate_limit_exceeded",
                    "detail": f"{ANON_PATH_LIMIT.amount} per 10 second",
                }
            },
            headers={
                "Retry-After": _RETRY_AFTER_S,
                "X-RateLimit-Limit": str(ANON_PATH_LIMIT.amount),
                "X-RateLimit-Remaining": "0",
            },
        )
        await response(scope, receive, send)

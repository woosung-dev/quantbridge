# Sprint 61 T-5 (BL-311) — BE 응답 보안 헤더 + server 헤더 info-leak strip
"""ASGI middleware that injects baseline security headers on every response.

Multi-Agent QA 2026-05-17 발견 (BL-311): BE 응답에 X-Frame-Options / HSTS /
X-Content-Type-Options / Referrer-Policy / Permissions-Policy 0건 + `server: uvicorn`
version disclosure (OWASP A05:2021). FE 와 비대칭. Production 보안 audit 즉시 지적.

본 미들웨어는 응답에 5 헤더 baseline 부착 + `server` 헤더 strip. HSTS 는 production
환경에서만 부착 (HTTPS 가정). CORS / rate-limit / exception handler 와 독립.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

DispatchCallable = Callable[[Request], Awaitable[Response]]


_BASELINE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """모든 응답에 baseline 보안 헤더 부착 + server 헤더 strip.

    Args:
        app: ASGI app.
        enable_hsts: True 시 Strict-Transport-Security 부착 (production HTTPS 가정).
    """

    def __init__(self, app: ASGIApp, enable_hsts: bool = False) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: DispatchCallable) -> Response:
        response = await call_next(request)
        for header, value in _BASELINE_HEADERS.items():
            response.headers.setdefault(header, value)
        if self.enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        # ★★[BL-347] **이 줄은 uvicorn 의 `Server` 헤더를 지우지 못한다.**
        #   uvicorn 은 그 헤더를 ASGI 바깥 **프로토콜 계층**에서 붙이므로 미들웨어가
        #   보는 `response.headers` 에는 애초에 없다. 실측(2026-08-16, 로컬 8경로):
        #   플래그 없이 띄우면 `/health`~`/nonexistent` **전부** `server: uvicorn` 을 냈고,
        #   `--no-server-header` 를 붙이자 8/8 이 사라졌다.
        #   ⇒ **실효 수단은 기동 플래그 하나**이고(`docker-entrypoint.sh` · `Makefile` ·
        #   서버 systemd 유닛), 이 줄은 앱이 스스로 `server` 를 넣는 경우만 덮는다.
        #   ★종전 회귀 테스트는 `TestClient` 라 그 헤더가 원래 없어 **항진명제**였다 —
        #   지금은 `tests/test_uvicorn_server_header.py` 가 기동 명령을 직접 잰다.
        if "server" in response.headers:
            del response.headers["server"]
        return response

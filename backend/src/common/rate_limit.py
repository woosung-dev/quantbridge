"""Sprint 10 Phase B — slowapi Limiter factory + key/exceeded handlers.

- Storage: Phase A1 의 redis_lock_url (DB 3 격리) 재사용.
  실제 Redis 연결은 slowapi 첫 request hit 시 lazy 하게 생성 (import 시점 연결 없음).
- Key: Clerk JWT user_id (request.state.user_id 세팅 시 우선), 없으면 신뢰된 XFF leftmost / fallback request.client.host.
  현재 Phase B 는 IP-based 만 구현. request.state.user_id 는 향후 auth dependency 에서
  세팅 후 활성화 예정 (follow-up: Phase C/D).
- Fail-open: Redis 장애 시 swallow_errors=True 로 limiter 통과 + WARN 로그.
- 429 응답: X-RateLimit-* 헤더 (slowapi headers_enabled) + Retry-After 보강.
- qb_rate_limit_throttled_total Counter inc.
"""

from __future__ import annotations

import ipaddress
import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from src.common.metrics import qb_rate_limit_throttled_total
from src.core.config import settings

_LOGGER = logging.getLogger(__name__)


def _parse_trusted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Settings.trusted_proxies 를 IPv4/v6 Network 객체 리스트로 변환."""
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in settings.trusted_proxies:
        try:
            nets.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            _LOGGER.warning(
                "rate_limit_invalid_trusted_proxy",
                extra={"value": raw},
            )
    return nets


# 모듈 import 시 trusted_proxies 파싱 (settings 는 이미 초기화됨).
# 테스트에서 monkeypatch 로 교체 가능 (module-level 변수 직접 교체).
_TRUSTED_NETS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = _parse_trusted_networks()


def _client_ip_or_xff(request: Request) -> str:
    """신뢰된 proxy 뒤에서만 X-Forwarded-For 의 leftmost IP 사용. 그 외는 client.host."""
    client_host = get_remote_address(request)
    if not _TRUSTED_NETS:
        # 화이트리스트 비어 있으면 XFF 무시 + client.host 직접 사용
        return client_host
    try:
        client_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return client_host
    if not any(client_ip in net for net in _TRUSTED_NETS):
        # 요청 IP 가 신뢰된 proxy 대역이 아님 → XFF 신뢰 불가
        return client_host
    xff = request.headers.get("x-forwarded-for", "")
    if not xff:
        return client_host
    leftmost = xff.split(",")[0].strip()
    return leftmost or client_host


def rate_limit_key(request: Request) -> str:
    """Clerk JWT user_id 우선, 없으면 신뢰된 XFF / client.host.

    현재 Phase B: request.state.user_id 는 미세팅 상태 → 항상 IP fallback.
    향후 auth dependency 에서 request.state.user_id = user.id 세팅 시 user 기반 격리 활성화.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{_client_ip_or_xff(request)}"


def create_limiter() -> Limiter:
    """slowapi Limiter — Redis storage (Phase A1 pool URL 재사용) + fail-open + 100/min default.

    storage_uri 만 전달 → slowapi/limits 라이브러리가 첫 request hit 시 lazy 하게 연결.
    import 시점 Redis 연결 없음 (Phase A1 lazy 원칙 준수).
    """
    return Limiter(
        key_func=rate_limit_key,
        storage_uri=settings.redis_lock_url,
        # limits 라이브러리의 RedisStorage 가 sync redis.Redis 를 만들므로
        # async event loop 차단 방지 위해 socket timeout 강제 (codex Critical).
        # storage_options 는 redis.Redis(**options) 로 그대로 전달 (**options kwarg 지원 확인됨).
        # limits.storage.RedisStorage 의 **options 는 float|str|bool 수용.
        # slowapi Limiter 의 타입힌트는 Dict[str, str] 로 좁게 선언되어 있으나
        # 내부적으로 redis.Redis(**options) 에 float/bool 로 그대로 전달됨.
        # mypy 오탐 억제 (slowapi 라이브러리 타입 정의 오류 — Dict[str,str] 로 좁게 선언).
        storage_options={
            "socket_connect_timeout": 2.0,  # type: ignore[dict-item]
            "socket_timeout": 2.0,  # type: ignore[dict-item]
            "retry_on_timeout": False,  # type: ignore[dict-item]
        },
        default_limits=["100/minute"],
        swallow_errors=True,  # Redis 장애 → 통과 (fail-open)
        headers_enabled=True,  # X-RateLimit-* 헤더. slowapi 0.1.9 버그는 _RateLimitStateInitMiddleware 로 우회.
        in_memory_fallback_enabled=False,  # 분산 환경 정합성 우선
        strategy="fixed-window",
    )


async def rate_limit_exceeded_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """429 응답 + qb_rate_limit_throttled_total inc + X-RateLimit-* headers.

    slowapi 가 정상 path 에서는 `_inject_headers` 로 X-RateLimit-* 를 자동 추가
    하지만, exception 경로 (limit 초과 시 본 handler) 는 수동 보강 필요.
    request.state.view_rate_limit 에 `(RateLimitItem, List[str])` 튜플 있음.
    """
    from slowapi.errors import RateLimitExceeded as _RLE

    # endpoint label: route pattern (path param 포함 X) — cardinality 보호 (I2).
    route = request.scope.get("route")
    endpoint = route.path if route is not None and hasattr(route, "path") else request.url.path
    # 현재 Phase B 는 request.state.user_id 미세팅 → 항상 scope="ip".
    # Phase C/D 에서 auth dependency wire-up 후 scope="user" 활성 (follow-up).
    scope_label = "user" if getattr(request.state, "user_id", None) else "ip"
    qb_rate_limit_throttled_total.labels(scope=scope_label, endpoint=endpoint).inc()

    detail_msg = exc.detail if isinstance(exc, _RLE) else str(exc)
    response = JSONResponse(
        status_code=429,
        content={
            "detail": {
                "code": "rate_limit_exceeded",
                "detail": str(detail_msg),
            }
        },
    )
    # X-RateLimit-* 헤더: request.state.view_rate_limit 이 세팅되어 있으면 사용.
    # view_rate_limit 은 (RateLimitItem, List[str]) 튜플 — _inject_headers 참조.
    view_rl = getattr(request.state, "view_rate_limit", None)
    if view_rl is not None:
        try:
            rl_item, _rl_keys = view_rl
            response.headers["X-RateLimit-Limit"] = str(rl_item.amount)
            response.headers["X-RateLimit-Remaining"] = "0"
            # reset_in 은 초 단위 (get_window_stats 반환값 기반) — slowapi _inject_headers 동일 방식.
            # view_rate_limit 은 hit 이전 window stat → reset 추정 불가. best-effort 60s 사용.
        except (TypeError, ValueError, AttributeError):
            pass  # view_rl 구조가 다르면 silent skip
    response.headers["Retry-After"] = "60"
    return response


class _RateLimitStateInitMiddleware(BaseHTTPMiddleware):
    """slowapi 0.1.9 버그 우회 — swallow_errors 경로에서 view_rate_limit 미설정 문제.

    slowapi async_wrapper 가 request.state.view_rate_limit 을 읽기 전에 None 으로
    초기화해 AttributeError 를 방지. Redis 장애 시 fail-open 경로가 깨지지 않음.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # slowapi 가 view_rate_limit 을 설정하지 못하는 경우(Redis 장애/exempt 경로) 방어
        request.state.view_rate_limit = None
        return await call_next(request)


def install_rate_limit(app: FastAPI) -> Limiter:
    """FastAPI 앱에 **module-level** limiter 바인딩 + slowapi middleware 등록.

    핵심: `app.state.limiter` 가 module-level `limiter` 와 동일 인스턴스여야
    라우터 데코레이터 (`@limiter.limit(...)`) 와 `app.state.limiter.exempt(...)`
    가 같은 카운터에서 동작한다. 새 Limiter 인스턴스를 만들면 exempt 가
    데코레이터에 반영되지 않음 (Phase B codex+Opus 평가 Critical).

    또한 `SlowAPIMiddleware` 를 반드시 등록해야 `default_limits=["100/minute"]`
    가 데코레이터 미적용 endpoint 에 적용됨. 없이는 `/api/v1/auth/me` 등
    무제한 (codex Critical).

    middleware 순서 (Starlette LIFO, 마지막 add 가 outermost):
    - _RateLimitStateInitMiddleware (outer) — view_rate_limit=None 선초기화
    - SlowAPIMiddleware (inner) — default_limits 체크 + X-RateLimit-* 헤더

    Returns the module-level limiter.
    """
    app.state.limiter = limiter  # module singleton 재사용
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(_RateLimitStateInitMiddleware)
    return limiter


# Module-level singleton — slowapi @limiter.limit("...") 데코레이터 호환용.
# import 시점에 Redis 연결 없음 (slowapi 는 storage_uri 만 저장, 첫 request hit 시 lazy 연결).
limiter = create_limiter()

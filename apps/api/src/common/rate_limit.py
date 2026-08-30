"""Sprint 10 Phase B — slowapi Limiter factory + key/exceeded handlers.

- Storage: Phase A1 의 redis_lock_url (DB 3 격리) 재사용.
  실제 Redis 연결은 slowapi 첫 request hit 시 lazy 하게 생성 (import 시점 연결 없음).
- Key: 검증된 JWT `sub` 우선(`_RateLimitIdentityMiddleware` 가 세운다), 없으면 신뢰된
  `CF-Connecting-IP` / XFF leftmost / fallback `request.client.host`.
  ★2026-08-16 [BL-754] 이전에는 `state.user_id` 를 **세우는 코드가 0건**이라 항상 IP 갈래였고,
  Cloudflare 뒤에서 `client.host` 가 전부 같아 **전 사용자가 한 버킷**이었다.
- Fail-open: Redis 장애 시 swallow_errors=True 로 limiter 통과 + WARN 로그.
- 429 응답: X-RateLimit-* 헤더 (slowapi headers_enabled) + Retry-After 보강.
- qb_rate_limit_throttled_total Counter inc.
"""

from __future__ import annotations

import ipaddress
import logging
from collections.abc import Awaitable, Callable

import anyio.to_thread
from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from src.common.metrics import qb_rate_limit_throttled_total
from src.core.config import Environment, secret_value, settings

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
    """신뢰된 proxy 뒤에서만 전달 헤더를 믿는다. 그 외는 client.host.

    ★**[BL-754] `CF-Connecting-IP` 를 `X-Forwarded-For` 보다 먼저 본다.**
    Cloudflare 는 기존 `X-Forwarded-For` 를 **덮어쓰지 않고 뒤에 붙인다** — 그래서 클라이언트가
    직접 `X-Forwarded-For: 1.2.3.4` 를 심으면 **leftmost 가 그 값이 된다.** 신뢰된 proxy
    뒤에서 leftmost 를 쓰는 것은 사실상 「키를 클라이언트가 고르게 하는 것」이고, 그러면
    한도가 무의미해진다. `CF-Connecting-IP` 는 Cloudflare 가 **덮어써서** 넣는 단일 값이다.
    XFF 갈래는 Cloudflare 가 아닌 proxy 를 위해 남긴다.
    """
    client_host = get_remote_address(request)
    if not _TRUSTED_NETS:
        # 화이트리스트 비어 있으면 전달 헤더 전부 무시 + client.host 직접 사용.
        # ★이것은 결함이 아니라 fail-safe 다 — 신뢰 근거 없이 헤더를 믿으면 위조로 한도를 벗어난다.
        #   프로덕션에서 이 갈래로 떨어지면 **모두가 한 버킷**이 되므로 `TRUSTED_PROXIES` 를 채워라.
        return client_host
    try:
        client_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return client_host
    if not any(client_ip in net for net in _TRUSTED_NETS):
        # 요청 IP 가 신뢰된 proxy 대역이 아님 → 전달 헤더 신뢰 불가
        return client_host
    cf_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cf_ip:
        return cf_ip
    xff = request.headers.get("x-forwarded-for", "")
    if not xff:
        return client_host
    leftmost = xff.split(",")[0].strip()
    return leftmost or client_host


def rate_limit_key(request: Request) -> str:
    """검증된 JWT `sub` 우선, 없으면 신뢰된 전달 헤더 / client.host.

    ★[BL-754] `request.state.user_id` 는 **`_RateLimitIdentityMiddleware` 가** 세운다.
    인증 `Depends` 로는 못 세운다 — `SlowAPIMiddleware` 는 ASGI 라 라우트 dependency 보다
    **먼저** 돌고, 그때는 `state.user_id` 가 아직 없다. 그래서 「auth dependency 한 줄」이라는
    처방은 성립하지 않는다(2026-08-16 실행 순서 실측).
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{_client_ip_or_xff(request)}"


def is_rate_limit_exempt_identity(email: str | None) -> bool:
    """[BL-784] 이 신원이 rate limit 면제 대상인가 — **두 조건이 모두** 참일 때만 참이다.

    ⑴ **`app_env` 가 정확히 `development` 다.** ⑵ 검증된 JWT 의 `email` 이 설정값과 정확히 같다.

    ★⑴ 은 화이트리스트다 — 「production 이 아니면」이 아니다. `is_production` 은 **staging 을
    거짓으로 본다**(`config.py:407`)므로 그 조건을 쓰면 staging 인스턴스에서 면제가 켜진다.
    같은 파일의 production validator 도 「backward-compat 위해 staging 은 강제하지 않음」이라
    적고 있어, 블랙리스트로 두면 staging 에는 **두 층 다 없는** 상태가 된다
    (2026-08-17 적대 리뷰 P1). 면제가 필요한 곳은 개발자 로컬과 CI 뿐이라 좁혀서 잃을 것이 없다.

    ★설정을 **먼저** 본다. 빈 값이 「전부 면제」로 뒤집히는 것이 이 판정의 유일한 파국이라
    비교보다 앞에 둔다 — 빈 설정에는 어떤 이메일도 걸리지 않는다.
    ★비교는 양쪽 다 `strip().lower()` 다. 이메일 로컬파트는 원칙적으로 대소문자를 구분하지만
    실제 제공자는 구분하지 않고, 여기서 구분하면 「설정했는데 안 걸린다」가 조용히 생긴다.
    면제 대상은 우리가 만든 계정 하나뿐이라 넓혀서 잃을 것이 없다.
    """
    if settings.app_env != Environment.DEVELOPMENT.value:
        return False
    configured = settings.e2e_rate_limit_exempt_email.strip().lower()
    if not configured:
        return False
    if not email:
        return False
    return email.strip().lower() == configured


def create_limiter() -> Limiter:
    """slowapi Limiter — Redis storage (Phase A1 pool URL 재사용) + fail-open + 100/min default.

    storage_uri 만 전달 → slowapi/limits 라이브러리가 첫 request hit 시 lazy 하게 연결.
    import 시점 Redis 연결 없음 (Phase A1 lazy 원칙 준수).
    """
    return Limiter(
        key_func=rate_limit_key,
        storage_uri=secret_value(settings.redis_lock_url),
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


class _RateLimitIdentityMiddleware(BaseHTTPMiddleware):
    """[BL-754] `SlowAPIMiddleware` 보다 **먼저** 돌아 `request.state.user_id` 를 세운다.

    ★**이 미들웨어가 이 항목의 전부다.** 종전 `rate_limit_key` 는 `state.user_id` 를 읽는데
    그것을 세우는 코드가 레포에 **0건**이었다(주석이 「향후 auth dependency 에서」라고 적어 둔
    채로 남아 있었다). 그래서 실제로는 **항상 IP 갈래**였고, Cloudflare 뒤에서는 모든 사용자의
    `client.host` 가 같아 **전 사용자가 한 버킷**으로 붕괴했다.

    ★인증 `Depends` 로는 못 고친다 — `SlowAPIMiddleware` 는 ASGI 미들웨어라 라우트가 열리기
    **전에** 키를 계산한다. 그래서 등록을 `SlowAPIMiddleware` **뒤에** 해서(= 더 바깥에서
    먼저 돌게) 순서를 만든다. Starlette 는 나중에 add 한 것이 outermost 다.

    ★**문을 지키지 않는다.** 토큰이 없거나 깨졌으면 조용히 IP 로 떨어진다 — 거부는 인증
    dependency 의 일이고, 여기서 401 을 내면 공개 엔드포인트(`/waitlist` 등)가 죽는다.

    ★[BL-784] **면제 판정도 여기서 한다.** 판정에 필요한 `email` 은 이미 검증한 payload 안에
    있고, 이 미들웨어는 SlowAPI 보다 바깥이라 한도가 걸리기 **전**이다. 다른 곳에서 하려면
    토큰을 한 번 더 검증해야 한다.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.headers.get("authorization"):
            from src.realtime.auth import verified_claims_or_none

            # ★스레드로 넘긴다 — `_decode` 는 동기 crypto 이고 첫 요청엔 JWKS 를 가져온다.
            claims = await anyio.to_thread.run_sync(verified_claims_or_none, request)
            if claims:
                subject = claims.get("sub")
                if subject:
                    request.state.user_id = str(subject)
                if is_rate_limit_exempt_identity(claims.get("email")):
                    # ★`_rate_limiting_complete` 는 **slowapi 소유의 skip 플래그**다. slowapi 가
                    #   미들웨어 갈래(`middleware.py`)와 데코레이터 갈래(`extension.py`) **양쪽**
                    #   에서 이 이름을 보므로, 여기 한 줄이 `default_limits` 와 `@limiter.limit`
                    #   둘 다를 면제한다. 이름이 slowapi 것이라 업그레이드에 깨질 수 있지만,
                    #   깨지는 방향이 **한도가 다시 걸리는 쪽**이라 프로덕션 위험은 없다 —
                    #   깨지면 e2e 가 다시 흔들리고 판별력 테스트가 red 로 알려 준다.
                    request.state._rate_limiting_complete = True
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
    # ★[BL-754] 순서가 계약이다 — Identity 는 SlowAPI 보다 **바깥**이어야 키 계산 전에 돈다.
    #   이 줄을 SlowAPIMiddleware 위로 옮기면 per-user 격리가 조용히 사라진다.
    app.add_middleware(_RateLimitIdentityMiddleware)
    app.add_middleware(_RateLimitStateInitMiddleware)
    return limiter


# Module-level singleton — slowapi @limiter.limit("...") 데코레이터 호환용.
# import 시점에 Redis 연결 없음 (slowapi 는 storage_uri 만 저장, 첫 request hit 시 lazy 연결).
limiter = create_limiter()

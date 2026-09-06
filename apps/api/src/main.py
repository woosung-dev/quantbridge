"""FastAPI 애플리케이션 엔트리포인트.

`create_app()` 이 CORS·보안 헤더·rate limit 미들웨어 설치, AppException/unhandled
예외 핸들러 등록, 도메인 라우터(auth/strategy/backtest/trading/stress_test/optimizer 등)
마운트, `/health`·`/metrics` 엔드포인트 노출을 담당한다. `lifespan()` 은 CCXTProvider·
Redis lock pool·realtime listener 의 시작/종료 자원 라이프사이클을 관리한다.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST

from src.backtest.exceptions import StrategyDegraded, StrategyNotRunnable
from src.common.exceptions import AppException
from src.common.logging_config import configure_logging
from src.common.metrics_multiproc import mark_metrics_process_dead, render_metrics
from src.core.config import settings

# BL-561 — uvicorn 기본 LOGGING_CONFIG 는 `uvicorn*` 만 설정하고 **root 엔 핸들러를 두지
# 않는다** → `src.*` 는 `logging.lastResort`(WARNING) 로 떨어져 INFO 가 통째로 사라졌다.
# ★app import 시점에 세운다: uvicorn 은 자기 dictConfig 를 먼저 돌린 뒤 `src.main:app` 을
# import 하므로 우리 설정이 나중에 와서 이긴다. celery 는 `tasks/celery_app.py` 의
# `setup_logging` 시그널이 같은 함수를 부른다 — 두 프로세스가 같은 포맷을 쓴다.
configure_logging()


async def app_exc_handler(_req: Request, exc: Exception) -> JSONResponse:
    """AppException → JSONResponse 직렬화 (spec §4.4).

    code 속성이 설정된 예외는 `{"detail": {"code": ..., "detail": ...}}` 형식으로
    Frontend 가 code 로 분기 가능. Sprint 21 (codex G.0 P1 #5): StrategyNotRunnable
    은 추가로 `unsupported_builtins: list[str]` 노출 — FE 가 string split 하지 않고
    구조화된 list 직접 사용. module-level 로 추출되어 test 에서도 import 가능.

    Sprint 32 E (BL-163): StrategyNotRunnable / StrategyDegraded 둘 다 사용자 친화
    `friendly_message: str` 필드 노출. FE 가 toast 또는 inline 카드 헤더로 활용.

    signature 의 `exc: Exception` 은 Starlette `add_exception_handler` 호환을 위함.
    runtime 에선 AppException subclass 만 dispatch 됨 (FastAPI 가 type narrowing).
    """
    if not isinstance(exc, AppException):
        # 정상 흐름에선 발생 안 함 — Starlette 가 AppException subclass 만 라우팅.
        # 안전 fallback (예외적 호출 시 500).
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    if exc.code is not None:
        body: dict[str, object] = {
            "detail": {"code": exc.code, "detail": exc.detail},
        }
        if isinstance(exc, StrategyNotRunnable):
            detail_dict = body["detail"]
            assert isinstance(detail_dict, dict)
            detail_dict["unsupported_builtins"] = exc.unsupported_builtins
            detail_dict["friendly_message"] = exc.friendly_message
        elif isinstance(exc, StrategyDegraded):
            detail_dict = body["detail"]
            assert isinstance(detail_dict, dict)
            detail_dict["degraded_calls"] = exc.degraded_calls
            detail_dict["friendly_message"] = exc.friendly_message
    else:
        body = {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=body)


def _scrub_validation_input(node: object) -> object:
    """validation error 트리에서 `input` 키를 **깊이 무관하게** 제거한다.

    pydantic v2 의 error dict 는 union / 중첩 모델에서 `ctx` 안에 또 다른 error list 를
    담을 수 있으므로 최상위만 지우면 샌다. list/dict 를 재귀로 훑는다.
    """
    if isinstance(node, dict):
        return {k: _scrub_validation_input(v) for k, v in node.items() if k != "input"}
    if isinstance(node, list):
        return [_scrub_validation_input(v) for v in node]
    return node


async def validation_exc_handler(_req: Request, exc: Exception) -> JSONResponse:
    """422 응답에서 **요청 원문(`input`)을 제거**한다 (2026-08-15 surface-truth).

    FastAPI 기본 핸들러는 `exc.errors()` 를 그대로 직렬화하는데, pydantic v2 의 error
    dict 는 `"input"` 에 **검증에 실패한 값 그 자체**를 담는다. `mode="after"` validator
    는 body 파싱 **뒤에** 돌기 때문에 `loc == ["body"]` 인 에러의 `input` 은 **요청 body
    전체**다 — 실측(2026-08-15):

        POST /trading/accounts {"exchange":"okx", ..., "api_secret":"SUPER_SECRET_VALUE"}
        → 422 {"detail":[{... "input":{"api_key":"AKIA_REAL_KEY",
                                        "api_secret":"SUPER_SECRET_VALUE"}}]}

    거래소 API secret 평문이 응답 body 로 되돌아오면 브라우저 콘솔·프록시 로그·에러
    텔레메트리에 남는다. 트리거는 현실적이다 — OKX 등록 시 passphrase 누락 하나면 된다.

    ★**스키마 타입(`SecretStr`) 마스킹에 의존하지 않는다.** 이건 전역 경계 수리라
    `RegisterAccountRequest` 뿐 아니라 **모든** 라우트의 422 에 동시에 적용된다.
    `loc`/`msg`/`type` 은 유지한다 — FE 가 어느 필드가 틀렸는지 알아야 하고, 그 셋은
    값이 아니라 값의 **위치와 규칙**이다.

    응답 봉투는 FastAPI 기본과 **같은 모양**(`{"detail": [...]}`)을 유지한다 — 이 수리는
    노출을 없애는 것이지 계약을 바꾸는 것이 아니다.
    """
    if not isinstance(exc, RequestValidationError):
        # 정상 흐름에선 발생 안 함 — Starlette 가 RequestValidationError 만 라우팅.
        return JSONResponse(status_code=422, content={"detail": "Validation error"})

    return JSONResponse(
        status_code=422,
        content={"detail": _scrub_validation_input(jsonable_encoder(exc.errors()))},
    )


async def unhandled_exc_handler(_req: Request, exc: Exception) -> JSONResponse:
    """Sprint 32 E (BL-163): 표준화된 5xx 응답.

    AppException subclass 외 모든 unhandled exception 을 catch 하여
    `{"detail": "..."}` 형태로 정규화. 빈 body / HTML 페이지 / stack trace
    유출을 차단하고 FE 가 일관된 toast 메시지를 표시하도록 보장.

    debug=True 일 때 (개발 환경) 만 exc.__class__.__name__ 노출 — production
    에서는 generic message ("Internal server error. 잠시 후 다시 시도해 주세요.").
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.exception("unhandled exception in request handler", exc_info=exc)

    # production: stack trace / class 이름 노출 차단 (정보 leak risk).
    # dev/test (debug=True): exc class 노출 — FE/QA 가 빠르게 root cause 파악.
    if settings.debug:
        message = f"Internal server error: {exc.__class__.__name__}. 잠시 후 다시 시도해 주세요."
    else:
        message = "Internal server error. 잠시 후 다시 시도해 주세요."

    return JSONResponse(
        status_code=500,
        content={"detail": message},
    )


def _metrics_auth_token() -> str | None:
    """`/metrics` 가 요구하는 토큰. 미설정·빈 문자열은 **둘 다 「없음」**이다.

    ★엔드포인트 가드와 부팅 로그가 **이 술어 하나**를 공유한다([BL-704]). 두 벌로 두면
    로그가 「활성」이라 말하는데 스크레이프는 401 인 상태가 생기고, 그 어긋남은
    운영자에게 보이지 않는다 — 이 회차가 고치는 병과 정확히 같은 모양이다.
    """
    token = settings.prometheus_bearer_token
    if token is None:
        return None
    return token.get_secret_value() or None


def _verify_prometheus_bearer(
    authorization: str | None = Header(default=None),
) -> None:
    """Prometheus 스크래퍼 용 bearer token 검증 (Sprint 9 Phase D).

    Grafana Cloud Agent 가 `settings.prometheus_bearer_token` 과 같은 값을
    `Authorization: Bearer` 로 보내야 scrape 를 허용한다.

    ★**토큰 미설정은 allow 가 아니라 deny 다** (2026-08-11 ledger-truth). 종전에는
    미설정 시 `return` 으로 통과시켰고, 그게 BL-246 이 지적한 「public /metrics」의
    실제 표면이었다 — production 은 `core/config.py` 의 validator 가 부팅을 막아
    안전했지만 **그 외 모든 환경**(dev·local·스테이징·컨테이너 오조립)은 무인증 노출이다.
    fail-open 을 fail-closed 로 뒤집는다.

    ★★**「production 에서는 토큰이 항상 있으므로 이 분기는 발화하지 않는다」로 읽지 마라 —
    그 문장이 이 회차의 오류였다.** `core/config.py:369` 의 가드는 `app_env` 문자열이
    정확히 `production` 일 때만 돈다(staging 은 `:367` 이 명시적으로 면제). 그런데
    **이 레포의 실배포 호스트는 `APP_ENV` 를 아예 설정하지 않아 기본값 `development` 로
    돈다**(`config.py:33` · `docs/operations/frontend-deploy.md:13`). 즉 그 호스트는
    부팅 가드의 보호를 **받지 않는다.**

    2026-08-11 실측 — 그 호스트의 `.env.local` 에는 토큰이 **설정돼 있다**(비어 있지 않음).
    그래서 오늘 스크레이프는 깨지지 않는다. 하지만 그것을 보장하는 것은 **운영자의 손**이었다
    ⇒ `.env.local` 을 재프로비저닝하면서 이 줄을 빠뜨리면 `/metrics` 가 **조용히 401** 이
    되고 부팅은 성공한다.

    ★[BL-704] — 그 공백은 이제 **부팅 로그 1줄**이 알린다(`lifespan()`). 부팅을 막지는
    않는다(dev 를 깨지 않는다). 판정은 `_metrics_auth_token()` 하나를 공유하므로 로그와
    이 가드가 갈라질 수 없다.
    """
    expected = _metrics_auth_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer token required (PROMETHEUS_BEARER_TOKEN unset)",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer token required",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid bearer token",
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown 자원 라이프사이클.

    - CCXTProvider singleton (ohlcv_provider=timescale 일 때만)
    - Redis lock pool healthcheck (Sprint 10 A1) — 실패 시 degraded 모드
    - Sprint 23 BL-103: EXCHANGE_PROVIDER deprecation warning (staging/production)
    - BL-704: `/metrics` 인증 활성 여부 1줄 (모든 환경 · 부팅을 막지 않는다)
    """
    # BL-704 — `/metrics` 인증 상태를 **부팅 시점에** 말한다. 다른 자원보다 먼저 찍는다:
    # 뒤쪽 startup 이 죽어도 이 사실은 로그에 남아야 한다.
    #
    # ★**`app_env` 로 감싸지 않는다.** 이 항목의 병이 정확히 그것이다 — `core/config.py` 의
    #   production validator 는 `app_env` **문자열**이 `production` 일 때만 돌고(staging 은
    #   명시 면제), 이 레포의 실배포 호스트는 `APP_ENV` 를 아예 설정하지 않아 기본값
    #   `development` 로 돈다(`frontend-deploy.md:13`). 즉 **보호를 가장 못 받는 환경이
    #   경고도 못 받는** 상태였다. `app_env` 는 조건이 아니라 **찍는 값**이다.
    #
    # ★fail-closed 이므로 「토큰 없음」의 결과는 노출이 아니라 **관측 상실**이다 —
    #   스크레이프가 전건 401 이 되고 부팅은 성공한다. `curl /metrics` 의 401 만으로는
    #   「보호 중」과 「관측 상실」을 **가를 수 없다**(`frontend-deploy.md` §4). 이 줄이 판별자다.
    import logging

    _boot_logger = logging.getLogger(__name__)
    if _metrics_auth_token():
        _boot_logger.info("metrics_auth=enabled app_env=%s", settings.app_env)
    else:
        _boot_logger.warning(
            "metrics_auth=DISABLED app_env=%s — PROMETHEUS_BEARER_TOKEN 미설정이라 "
            "/metrics 는 모든 스크레이프에 401 이다 (관측 상실, 부팅은 계속한다). "
            "실배포 호스트라면 .env.local 의 그 줄이 빠졌는지 확인해라 [BL-704]",
            settings.app_env,
        )

    # Sprint 23 BL-103 — EXCHANGE_PROVIDER 가 dispatch path 미사용 (Sprint 22 BL-091).
    # staging/production 에서 non-default 값 설정 시 운영자에게 명시 warning.
    # development/test 는 silent (test_config.py 4건이 EXCHANGE_PROVIDER setenv).
    if settings.exchange_provider != "fixture" and settings.app_env in ("staging", "production"):
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "EXCHANGE_PROVIDER=%s is DEPRECATED (Sprint 22 BL-091). "
            "dispatch 는 ExchangeAccount.exchange + mode + Order.leverage 기반. "
            "본 env 는 Sprint 23+ 제거 예정.",
            settings.exchange_provider,
        )

    if settings.ohlcv_provider == "timescale":
        from src.market_data.providers.ccxt import CCXTProvider

        app.state.ccxt_provider = CCXTProvider(exchange_name=settings.default_exchange)
    else:
        app.state.ccxt_provider = None

    from src.common.redis_client import healthcheck_redis_lock

    await healthcheck_redis_lock(app)

    # Redis listener는 healthcheck와 동일하게 best-effort다. 장애는 listener 내부의
    # backoff 재연결로 흡수하고 HTTP/WS 앱 기동은 계속한다.
    from src.realtime.manager import ConnectionManager

    app.state.realtime_manager = ConnectionManager()
    app.state.realtime_listener_task = asyncio.create_task(app.state.realtime_manager.listen())

    yield

    try:
        app.state.realtime_listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state.realtime_listener_task
        await app.state.realtime_manager.close()

        if getattr(app.state, "ccxt_provider", None) is not None:
            await app.state.ccxt_provider.close()
    finally:
        try:
            mark_metrics_process_dead()
        except Exception:
            import logging

            logging.getLogger(__name__).exception("metrics_process_dead_mark_failed_on_shutdown")


def create_app() -> FastAPI:
    # Sprint 61 T-4 (BL-312): OpenAPI / Swagger UI / Redoc 익명 노출 차단.
    # ★2026-08-15 surface-truth — 판정을 `is_production` 에서 `debug` 로 옮겼다.
    #   `is_production` 은 **배포 호스트가 `APP_ENV` 를 넣었을 때만** 참이라, 넣지 않은
    #   실배포(`qb-api.woosung.dev`)에서 `/docs`·`/openapi.json` 이 **인터넷에 200** 이었다
    #   (2026-08-15 실측). 그 호스트는 Cloudflare Access 뒤도 아니다 — `frontend-deploy.md:48`
    #   이 「`qb-api.woosung.dev` 에는 Access 를 걸지 마라」고 적어 뒀다.
    #   ⇒ 노출은 **명시적 opt-in**(`DEBUG=true`)일 때만. 새 설정을 만들지 않고 기존
    #   `debug` 를 「신뢰된 로컬」 단일 스위치로 재사용한다.
    #   ★`is_production` 항은 남긴다 — 이중 방어다. `app_env` 를 런타임에 바꿔도
    #   (테스트가 그렇게 한다) production 은 debug 값과 무관하게 무조건 숨긴다.
    _hide_docs = settings.is_production or not settings.debug
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=None if _hide_docs else "/docs",
        redoc_url=None if _hide_docs else "/redoc",
        openapi_url=None if _hide_docs else "/openapi.json",
    )

    # Phase A2/B 가 본 플래그를 평가하기 전 lifespan 이 healthcheck 호출.
    # startup 미진입 / 테스트가 lifespan 우회 시 AttributeError 봉쇄용 기본값.
    app.state.redis_lock_healthy = False

    # Sprint 10 Phase B — rate limit middleware (slowapi + Redis storage DB 3)
    from src.common.rate_limit import install_rate_limit

    install_rate_limit(app)

    # 2026-09-06 데이터 경로 조사 3-C — 와일드카드 2종을 명시 목록으로.
    #   요청 헤더: FE 는 `Authorization`·`Content-Type` 만 보내고 `Idempotency-Key` 는 BE 계약이다
    #   (`backtest/router.py`). 노출 헤더: 종전엔 `expose_headers` 가 없어 브라우저가
    #   `X-RateLimit-*`·`Retry-After`·`X-Idempotency-Replayed` 를 **읽을 수 없었다**(서버는 내고 있었다).
    #   `max_age` 600 은 Starlette 기본값과 같지만 계약으로 적어 둔다 — preflight 를 요청마다 안 돈다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
            "X-Idempotency-Replayed",
            "Idempotency-Replayed",
        ],
        max_age=600,
    )

    # Sprint 61 T-5 (BL-311) — baseline 보안 헤더 + server 헤더 info-leak strip.
    # CORS 직후 등록 → 모든 응답 (preflight 포함) 에 X-Frame / nosniff / Referrer /
    # Permissions 부착. HSTS 는 **로컬 개발이 아닐 때** 부착한다.
    # ★2026-08-15 surface-truth — 종전 `is_production` 은 `APP_ENV` 미설정 배포 호스트를
    #   놓쳤다(`_hide_docs` 와 같은 뿌리). HSTS 헤더는 스펙상 **HTTP 응답에서는 브라우저가
    #   무시**하므로 평문 로컬에 켜도 해가 없고, HTTPS 배포에서는 켜져야 한다.
    from src.common.security_headers import SecurityHeadersMiddleware

    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=settings.is_production or not settings.debug,
    )

    app.add_exception_handler(AppException, app_exc_handler)

    # 2026-08-15 surface-truth — 422 body 에서 요청 원문(`input`) 제거.
    # FastAPI 기본 핸들러가 거래소 API secret 평문을 응답에 되돌려 주고 있었다(실측).
    app.add_exception_handler(RequestValidationError, validation_exc_handler)

    # Sprint 32 E (BL-163): unhandled Exception 표준 5xx 응답.
    # FastAPI default 500 ("Internal Server Error" plain) 대신 JSON `{detail: ...}`
    # 로 정규화 → FE 의 readErrorBody 가 일관 dict 반환 + toast 표시.
    # AppException 은 위 handler 가 먼저 dispatch (priority).
    app.add_exception_handler(Exception, unhandled_exc_handler)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    # Sprint 30 ε B3 — /healthz readiness probe (Postgres / Redis / Celery)
    from src.health.router import router as health_router

    app.include_router(health_router)

    @app.get(
        "/metrics",
        include_in_schema=False,
        dependencies=[Depends(_verify_prometheus_bearer)],
    )
    async def metrics_endpoint() -> Response:
        """Prometheus text exposition format (Sprint 9 Phase D).

        세션 인증 제외, bearer token (settings.prometheus_bearer_token) 으로 보호.
        토큰이 None/empty 면 **모든 요청이 401** 이다 (2026-08-11 fail-closed 전환).
        """
        return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)

    # Sprint 10 Phase B — /metrics, /health 는 rate limit 면제
    # (Prometheus 스크래퍼 + health-check 는 무제한 허용)
    # Sprint 30 ε B3 — /healthz readiness probe 도 면제 (Cloud Run liveness scrape)
    app.state.limiter.exempt(metrics_endpoint)
    app.state.limiter.exempt(health)
    for route in health_router.routes:
        if hasattr(route, "endpoint"):
            app.state.limiter.exempt(route.endpoint)

    # Sprint 10 Phase B — /api/v1/webhooks/* 는 TradingView alert 수신. HMAC 인증이
    # primary 보안 레이어이므로 default 100/min 제외. high-freq strategy 시
    # alert drop 방지 (Sonnet review Critical).
    from src.trading.router import router as _trading_router

    for route in _trading_router.routes:
        if (
            hasattr(route, "path")
            and route.path.startswith("/webhooks")
            and hasattr(route, "endpoint")
        ):
            app.state.limiter.exempt(route.endpoint)

    # 도메인 라우터는 Stage 3 스프린트에서 순차 등록
    from src.auth.router import router as auth_router

    app.include_router(auth_router, prefix="/api/v1")

    from src.strategy.router import router as strategy_router

    app.include_router(strategy_router, prefix="/api/v1")

    from src.backtest.router import router as backtest_router

    app.include_router(backtest_router, prefix="/api/v1")

    from src.trading.router import router as trading_router

    app.include_router(trading_router, prefix="/api/v1")

    from src.stress_test.router import router as stress_test_router

    app.include_router(stress_test_router, prefix="/api/v1")

    # Sprint 54 — Phase 3 Optimizer Grid Search MVP
    from src.optimizer.router import router as optimizer_router

    app.include_router(optimizer_router, prefix="/api/v1")

    # [ADR-040] LLM provider 모델 카탈로그 — 설정한 모델이 provider 목록에 실재하는지 본다
    from src.strategy.narrative.router import router as llm_router

    app.include_router(llm_router, prefix="/api/v1")

    # pine-compat-experiment — indicator → strategy 변환
    from src.strategy.convert.router import router as convert_router

    app.include_router(convert_router, prefix="/api/v1")

    # Sprint 11 Phase C — Waitlist domain
    from src.waitlist.router import router as waitlist_router

    app.include_router(waitlist_router, prefix="/api/v1")

    from src.realtime.router import router as realtime_router

    app.include_router(realtime_router, prefix="/api/v1")

    return app


app = create_app()

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.backtest.exceptions import StrategyNotRunnable
from src.common.exceptions import AppException
from src.core.config import settings


async def app_exc_handler(_req: Request, exc: Exception) -> JSONResponse:
    """AppException → JSONResponse 직렬화 (spec §4.4).

    code 속성이 설정된 예외는 `{"detail": {"code": ..., "detail": ...}}` 형식으로
    Frontend 가 code 로 분기 가능. Sprint 21 (codex G.0 P1 #5): StrategyNotRunnable
    은 추가로 `unsupported_builtins: list[str]` 노출 — FE 가 string split 하지 않고
    구조화된 list 직접 사용. module-level 로 추출되어 test 에서도 import 가능.

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
    else:
        body = {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=body)


def _verify_prometheus_bearer(
    authorization: str | None = Header(default=None),
) -> None:
    """Prometheus 스크래퍼 용 bearer token 검증 (Sprint 9 Phase D).

    settings.prometheus_bearer_token 이 설정된 경우에만 검증 활성.
    비어 있으면 검증 스킵 (로컬 개발용). Grafana Cloud Agent 가 동일 토큰을
    `bearer_token` 헤더로 전송해야 scrape 허용.
    """
    expected = (
        settings.prometheus_bearer_token.get_secret_value()
        if settings.prometheus_bearer_token is not None
        else None
    )
    if not expected:
        return  # 토큰 미설정 시 allow — dev/local 용
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
    """
    # Sprint 23 BL-103 — EXCHANGE_PROVIDER 가 dispatch path 미사용 (Sprint 22 BL-091).
    # staging/production 에서 non-default 값 설정 시 운영자에게 명시 warning.
    # development/test 는 silent (test_config.py 4건이 EXCHANGE_PROVIDER setenv).
    if (
        settings.exchange_provider != "fixture"
        and settings.app_env in ("staging", "production")
    ):
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

    yield

    if getattr(app.state, "ccxt_provider", None) is not None:
        await app.state.ccxt_provider.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Phase A2/B 가 본 플래그를 평가하기 전 lifespan 이 healthcheck 호출.
    # startup 미진입 / 테스트가 lifespan 우회 시 AttributeError 봉쇄용 기본값.
    app.state.redis_lock_healthy = False

    # Sprint 10 Phase B — rate limit middleware (slowapi + Redis storage DB 3)
    from src.common.rate_limit import install_rate_limit

    install_rate_limit(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppException, app_exc_handler)

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

        Clerk 인증 제외, bearer token (settings.prometheus_bearer_token) 으로 보호.
        settings.prometheus_bearer_token 이 None/empty 면 인증 없이 접근 가능 (dev/local).
        """
        # 모듈 import — Histogram/Counter/Gauge 객체가 default REGISTRY 에 등록됨.
        # 여기서 import 하여 instrumentation 지점에서만 필요한 lazy binding.
        from src.common import metrics as _metrics  # noqa: F401  (ensure registration)

        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

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

    # Sprint 11 Phase C — Waitlist domain
    from src.waitlist.router import router as waitlist_router

    app.include_router(waitlist_router, prefix="/api/v1")

    return app


app = create_app()

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.common.exceptions import AppException
from src.core.config import settings


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
    """
    if settings.ohlcv_provider == "timescale":
        from src.market_data.providers.ccxt import CCXTProvider

        app.state.ccxt_provider = CCXTProvider(
            exchange_name=settings.default_exchange
        )
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppException)
    async def _app_exc_handler(_req: Request, exc: AppException) -> JSONResponse:
        # code 속성이 설정된 예외는 {"detail": {"code": ..., "detail": ...}} 형식으로
        # 직렬화해 Frontend가 code로 분기 처리 가능 (spec §4.4).
        if exc.code is not None:
            body: dict[str, object] = {
                "detail": {"code": exc.code, "detail": exc.detail},
            }
        else:
            body = {"detail": exc.detail}
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

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

    return app


app = create_app()

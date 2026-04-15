from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.common.exceptions import AppException
from src.core.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

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

    # 도메인 라우터는 Stage 3 스프린트에서 순차 등록
    from src.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/v1")

    return app


app = create_app()

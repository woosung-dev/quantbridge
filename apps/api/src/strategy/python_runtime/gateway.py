"""별도 Linux 실행기용 인증 gateway. 앱 서버에 Docker 권한을 주지 않는다."""

from __future__ import annotations

import argparse
import hmac
import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from decimal import Decimal
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from src.backtest.engine.python_adapter import run_python_backtest
from src.backtest.engine.types import BacktestConfig
from src.strategy.python_runtime.protocol import (
    MAX_BARS,
    MAX_SOURCE_BYTES,
    PythonRunnerUnavailable,
    PythonRuntimeError,
    PythonTransport,
)
from src.strategy.python_runtime.sandbox import DEFAULT_IMAGE, DockerPythonTransport
from src.strategy.python_runtime.serialization import (
    config_from_payload,
    frame_from_payload,
    funding_from_payload,
    provenance,
    result_payload,
)


class Bar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: AwareDatetime
    open: Decimal = Field(gt=0, allow_inf_nan=False)
    high: Decimal = Field(gt=0, allow_inf_nan=False)
    low: Decimal = Field(gt=0, allow_inf_nan=False)
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    volume: Decimal = Field(ge=0, allow_inf_nan=False)


class Funding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: AwareDatetime
    rate: Decimal = Field(allow_inf_nan=False)


class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: uuid.UUID
    source: str = Field(min_length=1, max_length=MAX_SOURCE_BYTES)
    bars: list[Bar] = Field(min_length=1, max_length=MAX_BARS)
    funding: list[Funding] | None = Field(default=None, max_length=MAX_BARS)
    params: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    warmup_bars: int = Field(default=0, ge=0, lt=MAX_BARS)


@dataclass
class _Job:
    cancelled: threading.Event = field(default_factory=threading.Event)
    transport: PythonTransport | None = None
    done: bool = False


def create_app(
    token: str,
    image: str = DEFAULT_IMAGE,
    *,
    transport_factory: Callable[[], PythonTransport] | None = None,
) -> FastAPI:
    """토큰은 파일/설정에서 주입한다. 실행 중 사용자 환경으로 전달하지 않는다."""
    if len(token) < 32:
        raise ValueError("실행기 토큰은 최소 32자여야 합니다")
    app = FastAPI(
        title="QuantBridge Python Runner", docs_url=None, redoc_url=None, openapi_url=None
    )
    slot = threading.Lock()
    guard = threading.Lock()
    jobs: OrderedDict[str, _Job] = OrderedDict()
    factory = transport_factory or (lambda: DockerPythonTransport(image))

    def authorized(request: Request) -> None:
        if not hmac.compare_digest(
            request.headers.get("authorization", "").encode(), ("Bearer " + token).encode()
        ):
            raise HTTPException(status_code=401, detail="실행기 인증이 필요합니다")

    def trim_jobs() -> None:
        # 취소 tombstone 도 남겨, HTTP 제출보다 취소가 먼저 도착하는 경쟁을 막는다.
        while len(jobs) > 4096:
            for key, job in jobs.items():
                if job.transport is None:
                    del jobs[key]
                    break
            else:
                break

    def execute(payload: BacktestRequest) -> dict[str, Any]:
        job_id = str(payload.job_id)
        with guard:
            if job_id in jobs:
                raise HTTPException(status_code=409, detail="이미 사용되거나 취소된 job_id 입니다")
            if not slot.acquire(blocking=False):
                raise HTTPException(
                    status_code=503, detail="Python 실행기가 다른 작업을 실행 중입니다"
                )
            job = _Job()
            jobs[job_id] = job
            trim_jobs()

        def tracked_factory() -> PythonTransport:
            transport = factory()
            with guard:
                cancelled = job.cancelled.is_set()
                if not cancelled:
                    job.transport = transport
            if cancelled:
                transport.close()
                raise PythonRuntimeError("Python 작업이 취소되었습니다")
            return transport

        try:
            unknown = set(payload.config) - {item.name for item in fields(BacktestConfig)}
            if unknown:
                raise PythonRuntimeError("알 수 없는 백테스트 설정입니다")
            config = config_from_payload(payload.config)
            bars = [item.model_dump(mode="json") for item in payload.bars]
            funding = (
                [item.model_dump(mode="json") for item in payload.funding]
                if payload.funding is not None
                else None
            )
            result = run_python_backtest(
                payload.source,
                frame_from_payload(bars),
                config,
                funding_from_payload(funding),
                payload.params,
                payload.warmup_bars,
                transport_factory=tracked_factory,
            )
            if job.cancelled.is_set():
                raise PythonRuntimeError("Python 작업이 취소되었습니다")
            image_id = getattr(job.transport, "image_id", "test-transport")
            return {
                **result_payload(result),
                "provenance": provenance(
                    payload.source,
                    bars,
                    funding,
                    payload.params,
                    result.config_used,
                    payload.warmup_bars,
                    image_id,
                ),
            }
        except PythonRunnerUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (PythonRuntimeError, ValueError, ArithmeticError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)[:500]) from exc
        finally:
            with guard:
                job.transport = None
                job.done = True
            slot.release()

    @app.post("/v1/backtests", dependencies=[Depends(authorized)])
    async def backtest(request: Request) -> dict[str, Any]:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 64 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="요청 크기 한도를 초과했습니다")
        try:
            payload = BacktestRequest.model_validate_json(bytes(body))
        except ValidationError as exc:
            # 소스/파라미터가 오류 로그나 응답에 재노출되지 않도록 입력값을 뺀다.
            raise HTTPException(
                status_code=422, detail=exc.errors(include_input=False, include_url=False)
            ) from exc
        return await run_in_threadpool(execute, payload)

    @app.post("/v1/backtests/{job_id}/cancel", dependencies=[Depends(authorized)])
    def cancel(job_id: uuid.UUID) -> dict[str, str]:
        key = str(job_id)
        with guard:
            job = jobs.setdefault(key, _Job())
            if job.done:
                return {"status": "completed"}
            job.cancelled.set()
            transport = job.transport
            trim_jobs()
        if transport is not None:
            transport.close()
        return {"status": "cancelled"}

    @app.get("/healthz", dependencies=[Depends(authorized)])
    def health() -> dict[str, Any]:
        if not slot.acquire(blocking=False):
            return {"available": True, "busy": True}
        transport = None
        try:
            transport = factory() if transport_factory else DockerPythonTransport(image, timeout=10)
            reply = transport.exchange(
                {
                    "type": "init",
                    "protocol": 1,
                    "source": "def on_bar(ctx, state): return {'action': 'hold'}",
                    "params": {},
                }
            )
            if reply != {"ready": 1}:
                raise PythonRunnerUnavailable("Python 실행기 프로토콜이 다릅니다")
            return {
                "available": True,
                "busy": False,
                "image_id": getattr(transport, "image_id", None),
            }
        except PythonRuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            if transport is not None:
                transport.close()
            slot.release()

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="QuantBridge 격리 Python 실행기")
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8190)
    args = parser.parse_args()
    token = args.token_file.read_text().strip()
    uvicorn.run(
        create_app(token, args.image), host=args.host, port=args.port, workers=1, access_log=False
    )


if __name__ == "__main__":
    main()

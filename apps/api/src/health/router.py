"""Sprint 30 ε B3 — ``/healthz`` readiness probe (Postgres / Redis / Celery).

Cloud Run / docker-compose healthcheck 는 본 endpoint 를 호출. 모든 dep 가 OK 일
때만 200 반환, 1+ fail 시 503 (Cloud Run 이 unhealthy traffic 차단 / restart).

설계 결정:
- Postgres: ``SELECT 1`` (engine.connect — pool_pre_ping 으로 stale 회피).
  timeout 5s.
- Redis: ``PING`` 또는 SET/GET round-trip 미수행 (lock pool 의 healthcheck
  helper 가 더 강한 verification 을 이미 lifespan 에 수행). timeout 5s.
- Celery: ``celery_app.control.inspect(timeout=3.0).ping()`` — broker 통해
  활성 worker 수 카운트. broker 다운 시 None / 빈 dict → 0 worker.
- 정책: Celery 0 worker 도 503 (api 인스턴스 단독 부팅 시점 race window 회피
  위해 backend prod 에서는 worker 1+ 필요).

테스트:
- ``apps/api/tests/health/test_health_extended.py`` 가 mock 으로 dep fail 시뮬.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, TypedDict

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["meta"])

# 각 dep 별 timeout (s)
_PG_TIMEOUT_S = 5.0
_REDIS_TIMEOUT_S = 5.0


def _get_celery_timeout_s() -> float:
    """Sprint 61 T-6 (BL-310) — celery inspect timeout env-driven (default 12.0).

    Multi-Agent QA 2026-05-17 발견:
    - 기존 3.0s 가 Docker isolated mode 의 broker round-trip 대비 너무 짧음 → false-503.
    - Sprint 61 fix 의 8.0s 도 부족 (uvicorn local ↔ docker worker cold-start 환경, BL-349 발견).
    - 12.0s 로 추가 완화 + env override 허용 (K8s readiness probe 환경별 조정).
    """
    try:
        return float(os.environ.get("HEALTHZ_CELERY_TIMEOUT_S", "12.0"))
    except (TypeError, ValueError):
        return 12.0


class HealthCheckResult(TypedDict):
    """healthz response payload schema."""

    db: str
    redis: str
    celery_workers: int


def _public_error(exc: BaseException) -> str:
    """익명 응답에 싣는 오류 문구 — 예외 **클래스 이름만** 준다.

    `str(exc)` 는 host:port · DB 이름 · role 을 담는다. `/healthz` 는 인증 없이 열려 있으므로
    상세는 위 `logger.warning` 에만 남긴다(보안 감사 2026-11-19).
    """
    return type(exc).__name__


async def _check_postgres() -> tuple[str, str | None]:
    """Postgres ``SELECT 1`` round-trip. Returns (status, error_msg)."""
    from sqlalchemy import text

    from src.common.database import engine

    try:
        async with asyncio.timeout(_PG_TIMEOUT_S):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return ("ok", None)
    except TimeoutError:
        return ("fail", f"timeout after {_PG_TIMEOUT_S}s")
    except Exception as exc:
        # health check 는 모든 dep error 흡수 — broad except 의도적.
        logger.warning("healthz_postgres_fail err=%s", exc)
        return ("fail", _public_error(exc))


async def _check_redis() -> tuple[str, str | None]:
    """Redis lock pool ``PING``. Returns (status, error_msg)."""
    from src.common.redis_client import get_redis_lock_pool

    try:
        async with asyncio.timeout(_REDIS_TIMEOUT_S):
            pool = get_redis_lock_pool()
            pong = await pool.ping()
        if not pong:
            return ("fail", "PING returned False")
        return ("ok", None)
    except TimeoutError:
        return ("fail", f"timeout after {_REDIS_TIMEOUT_S}s")
    except Exception as exc:
        logger.warning("healthz_redis_fail err=%s", exc)
        return ("fail", _public_error(exc))


async def _check_celery_workers() -> tuple[int, str | None]:
    """Celery worker count via control.inspect.ping. Returns (count, error_msg).

    broker 미가용 시 0 + error_msg. inspect 자체가 sync (broker round-trip) 라
    asyncio.to_thread 로 분리.
    """
    try:
        from src.tasks.celery_app import celery_app
    except Exception as exc:
        # import 자체 실패도 fail 로 카운트 — broad except 의도적.
        return (0, f"celery_app import failed: {exc}")

    timeout_s = _get_celery_timeout_s()
    try:
        # inspect는 수집 창 전체를 기다린다. 같은 시각의 바깥 취소가 정상 pong을 버리지 않게 한다.
        async with asyncio.timeout(timeout_s + 1.0):
            result = await asyncio.to_thread(
                lambda: celery_app.control.inspect(timeout=timeout_s).ping()
            )
        if not result:
            return (0, "no workers responded")
        # result = {worker_name: {ok: 'pong'}, ...}
        return (len(result), None)
    except TimeoutError:
        return (0, f"timeout after {timeout_s}s")
    except Exception as exc:
        logger.warning("healthz_celery_fail err=%s", exc)
        return (0, _public_error(exc))


_probe_inflight: asyncio.Task[tuple[int, dict[str, Any]]] | None = None


async def _probe() -> tuple[int, dict[str, Any]]:
    """Postgres → Redis → Celery 를 차례로 재고 (HTTP status, body) 를 만든다."""
    pg_status, pg_err = await _check_postgres()
    redis_status, redis_err = await _check_redis()
    celery_count, celery_err = await _check_celery_workers()

    body: dict[str, Any] = {
        "db": pg_status,
        "redis": redis_status,
        "celery_workers": celery_count,
    }

    errors: dict[str, str] = {}
    if pg_err:
        errors["db"] = pg_err
    if redis_err:
        errors["redis"] = redis_err
    if celery_err:
        errors["celery"] = celery_err

    if errors:
        body["errors"] = errors

    healthy = pg_status == "ok" and redis_status == "ok" and celery_count >= 1
    code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return code, body


async def _probe_single_flight() -> tuple[int, dict[str, Any]]:
    """동시에 들어온 `/healthz` 들이 **진행 중인 점검 한 벌을 공유**하게 한다.

    점검 한 벌은 앱 공용 DB 풀 1칸(최대 5초) · Redis 연결 1개 · 공유 스레드풀 1칸과
    broker 커넥션 1개(inspect 수집 창, 기본 12초)를 쥔다. `/healthz` 는 익명·rate limit
    면제라, 요청마다 새로 돌리면 동시 요청 수만큼 풀이 묶인다(보안 감사 2026-11-19 run-1·run-2).
    결과는 캐시하지 않는다 — 끝난 뒤의 요청은 새로 잰다.
    `shield` 는 한 호출자의 연결 끊김이 공유 작업을 취소하지 않게 한다.
    """
    global _probe_inflight
    if _probe_inflight is None or _probe_inflight.done():
        _probe_inflight = asyncio.ensure_future(_probe())
    return await asyncio.shield(_probe_inflight)


@router.get("/healthz", include_in_schema=True)
async def healthz() -> JSONResponse:
    """Readiness probe — Postgres + Redis + Celery 3-dep round-trip.

    Returns:
        200 + ``{"db": "ok", "redis": "ok", "celery_workers": N}``: 모든 dep OK + worker ≥ 1.
        503 + ``{"db": "ok"|"fail", "redis": ..., "celery_workers": N, "errors": {...}}``:
            1+ dep fail OR celery_workers == 0.
    """
    code, body = await _probe_single_flight()
    return JSONResponse(status_code=code, content=body)


@router.get("/livez", include_in_schema=True)
async def livez() -> JSONResponse:
    """Sprint 61 T-6 (BL-310) — Liveness probe (broker-skip, process up 만 확인).

    /healthz 는 Postgres + Redis + Celery 3-dep readiness 검증 (K8s readiness probe).
    /livez 는 process up 만 검증 (K8s liveness probe) — dep 가 일시 fail 해도
    process 자체는 살아있으면 200 → K8s 가 의미 없는 restart 안 함.

    Multi-Agent QA 2026-05-17 (BL-310): /healthz 3s celery timeout false-503 가
    K8s readiness probe → liveness probe 동시 적용 시 restart loop 위험. probe
    역할 분리로 차단.
    """
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "alive"})

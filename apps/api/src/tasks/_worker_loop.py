"""Sprint 18 BL-080 — Persistent worker event loop helper (Option C).

Sprint 17 의 per-call `create_worker_engine_and_sm()` + finally `engine.dispose()`
가 같은 Celery prefork child 의 2nd+ task 에서 `RuntimeError("Future ... attached
to a different loop")` / `InterfaceError("another operation is in progress")` 로
fail 하는 문제 (BL-080) 의 architectural fix.

문제 본질
=========
Celery prefork worker 의 매 task 가 `asyncio.run()` 으로 새 event loop 를 만들면,
asyncpg connection 의 transport 가 *생성 당시 loop* 의 transport waiter 를 capture
한다. 1st task 의 `engine.dispose()` 가 connection 을 close 시도해도, internal
asyncpg/SQLAlchemy state (BaseProtocol callbacks, prepared statement cache 등) 가
그 loop 의 Future 를 strong-reference 하여 garbage 되지 않는다. 2nd task 가 새
loop 에서 동일 module-level 객체 (또는 새 connection 이지만 stale internal cache)
를 await 시 "different loop" 발생.

해결책 (Option C)
=================
worker child fork 직후 1회 `asyncio.new_event_loop()` 로 영속 loop 를 만들고,
모든 task entry point 가 `asyncio.run()` 대신 `_WORKER_LOOP.run_until_complete(coro)`
로 동일 loop 재사용. asyncpg/SQLAlchemy 의 모든 async state 가 같은 loop 에 bind
되므로 stale loop reference 가 발생할 수 없다.

라이프사이클 hook (codex G.0 P1 #4 반영)
========================================
- `init_worker_loop()` — `worker_process_init` signal (prefork child fork 후 1회).
- `shutdown_worker_loop()` — `worker_process_shutdown` signal (prefork child shutdown).
  `worker_shutdown` 은 master process / solo pool 만 시그널 → 별도 호환 path 에서
  본 함수를 idempotent 하게 호출.

호환성 (codex G.0 P1 #6 반영)
=============================
`run_in_worker_loop()` 는 nested running loop (pytest-asyncio / celery_eager) 안에서
호출되면 `asyncio.run()` 의 silent fallback 대신 명시적 `RuntimeError` raise 한다.
조용한 실패가 디버깅을 어렵게 만들기 때문 — 호출자가 coroutine 을 직접 await 하도록
유도.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Worker child 의 영속 event loop. `worker_process_init` 에서 생성되어
# `worker_process_shutdown` 까지 모든 task 가 공유.
_WORKER_LOOP: asyncio.AbstractEventLoop | None = None

_T = TypeVar("_T")


def init_worker_loop() -> None:
    """Celery `worker_process_init` signal 에서 호출. child fork 후 1회.

    idempotent: 이미 살아있는 loop 가 있으면 재생성 안 함. shutdown 후 재호출 시
    새 loop 생성.
    """
    global _WORKER_LOOP
    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        _WORKER_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_WORKER_LOOP)


def shutdown_worker_loop() -> None:
    """Celery `worker_process_shutdown` signal 에서 호출 (codex G.0 P1 #4 반영).

    `worker_shutdown` 은 master process / solo pool 만 시그널 — prefork child
    cleanup 에는 부적합. (Sprint 12 의 backend-ws-stream `--pool=solo` 도 동일
    이유로 채택한 패턴)

    Cleanup 순서 (codex G.2 P2 #3 — `asyncio.run()` 동등성 확보):
    1. pending task cancel + drain
    2. async generator drain (`shutdown_asyncgens`)
    3. default executor shutdown (Python 3.9+ `shutdown_default_executor`)
    4. loop close

    drain 중 unhandled exception 이 발생해도 finally 에서 close 보장 — zombie 방지.
    idempotent: 이미 close 된 상태 또는 미초기화 상태면 no-op.

    **codex G.2 P1 #1 호환**: 본 함수는 `_on_worker_shutdown` 호출자 측에서 running
    loop 검사 후 호출되어야 한다. running 중에 본 함수 진입 시 `run_until_complete`
    가 RuntimeError raise.
    """
    global _WORKER_LOOP
    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        _WORKER_LOOP = None
        return

    loop = _WORKER_LOOP
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        # codex G.2 P2 #3 — `asyncio.run()` 의 cleanup 동등성. 누락 시 long-lived
        # loop 라 leak surface 누적 가능 (httpx async generator / aiohttp connector
        # async cleanup 등).
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            logger.exception("shutdown_asyncgens_failed")
        try:
            loop.run_until_complete(loop.shutdown_default_executor())
        except Exception:
            logger.exception("shutdown_default_executor_failed")
    except Exception:  # BLE001 — drain 실패해도 close 보장
        logger.exception("shutdown_worker_loop_pending_drain_failed")
    finally:
        try:
            loop.close()
        finally:
            _WORKER_LOOP = None


def run_in_worker_loop(coro: Coroutine[Any, Any, _T]) -> _T:
    """`asyncio.run()` 대체. Celery task entry point 에서 호출.

    동작 순서:
    1. `asyncio.get_running_loop()` 검사 — 이미 실행 중인 loop 가 있으면
       `RuntimeError` raise (codex G.0 P1 #6: pytest-asyncio / celery_eager
       안에서 호출 시 silent fallback 금지).
    2. `_WORKER_LOOP` 가 살아있으면 `run_until_complete(coro)` 로 영속 loop 재사용.
    3. `_WORKER_LOOP` 미초기화 (worker hook 미발화 상황 — ad-hoc CLI shell 등) +
       running loop 없음 → `asyncio.run(coro)` fallback.

    Args:
        coro: 실행할 coroutine. 한 번만 await 됨 (재실행 시 새 coroutine 전달 필수).

    Returns:
        coroutine 의 결과.

    Raises:
        RuntimeError: 이미 다른 event loop 가 실행 중인 환경에서 호출된 경우.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        # codex G.0 P1 #6 + G.2 P3 #1: silent fallback 으로 asyncio.run() 호출 시
        # "asyncio.run() cannot be called from a running event loop" 라는 모호한
        # 메시지. 명시적 안내로 디버깅 단축. coro.close() 로 "coroutine was never
        # awaited" warning 도 방지.
        coro.close()
        raise RuntimeError(
            "run_in_worker_loop() called from inside a running event loop. "
            "await the underlying coroutine directly instead. "
            "(pytest-asyncio / celery_eager / nested asyncio.run 호출 위치 점검)"
        )

    global _WORKER_LOOP
    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        return asyncio.run(coro)
    return _WORKER_LOOP.run_until_complete(coro)

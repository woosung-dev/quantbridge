"""Sprint 18 BL-080 — `_worker_loop` 단위 test (Option C persistent worker loop).

codex G.0 P1 #4/#5/#6 fix 검증:
- worker_process_shutdown 사용 (NOT worker_shutdown — master 만)
- run_in_worker_loop 가 nested running loop detect → RuntimeError
- _WORKER_LOOP 미초기화 + running loop 없음 → asyncio.run() fallback
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from src.tasks import _worker_loop


@pytest.fixture(autouse=True)
def _reset_worker_loop_module_state() -> Iterator[None]:
    """매 test 시작 + 끝 양쪽에서 module state 정리. 다른 test 에 누수 방지."""
    _worker_loop.shutdown_worker_loop()
    yield
    _worker_loop.shutdown_worker_loop()


def test_init_creates_loop_and_sets_as_thread_default() -> None:
    """init_worker_loop() 가 새 loop 를 생성하고 set_event_loop 로 thread default 설정."""
    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]

    _worker_loop.init_worker_loop()

    loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]
    assert loop is not None
    assert not loop.is_closed()
    # set_event_loop 호출 검증 — get_event_loop 가 동일 loop 반환
    assert asyncio.get_event_loop() is loop


def test_init_is_idempotent_when_loop_alive() -> None:
    """init 2회 연속 호출 시 동일 loop 유지. fork race 시 안전."""
    _worker_loop.init_worker_loop()
    first_loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]

    _worker_loop.init_worker_loop()
    second_loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]

    assert first_loop is second_loop


def test_init_replaces_closed_loop() -> None:
    """이전 loop 가 close 된 상태면 새로 생성. shutdown 후 재 init scenario."""
    _worker_loop.init_worker_loop()
    first_loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]
    assert first_loop is not None

    _worker_loop.shutdown_worker_loop()
    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]

    _worker_loop.init_worker_loop()
    second_loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]

    assert second_loop is not None
    assert second_loop is not first_loop


def test_run_in_worker_loop_returns_coroutine_result() -> None:
    """기본 happy path — coroutine 결과 반환."""
    _worker_loop.init_worker_loop()

    async def _coro() -> int:
        return 42

    result = _worker_loop.run_in_worker_loop(_coro())
    assert result == 42


def test_run_in_worker_loop_reuses_same_loop_across_calls() -> None:
    """**핵심 회귀 방어** — 매 호출마다 같은 loop 에서 실행.

    Sprint 17 의 asyncio.run() 패턴은 매번 새 loop 생성. 옵션 C 는
    `_WORKER_LOOP.run_until_complete` 로 동일 loop 재사용 → asyncpg connection
    의 transport waiter 가 stale loop 참조 안 함.
    """
    _worker_loop.init_worker_loop()
    expected_loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]

    captured_loops: list[asyncio.AbstractEventLoop] = []

    async def _capture() -> None:
        captured_loops.append(asyncio.get_running_loop())

    _worker_loop.run_in_worker_loop(_capture())
    _worker_loop.run_in_worker_loop(_capture())
    _worker_loop.run_in_worker_loop(_capture())

    assert len(captured_loops) == 3
    assert captured_loops[0] is expected_loop
    assert captured_loops[1] is expected_loop
    assert captured_loops[2] is expected_loop


def test_run_in_worker_loop_falls_back_to_asyncio_run_when_uninitialized() -> None:
    """_WORKER_LOOP 미초기화 + 실행 loop 없음 → asyncio.run() fallback.

    ad-hoc CLI shell 또는 worker 외부 호출 (e.g., management command) 호환.
    """
    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]

    async def _coro() -> int:
        return 7

    # 새 asyncio loop 가 생성되어 실행되고 close 됨 — fallback 동작
    result = _worker_loop.run_in_worker_loop(_coro())
    assert result == 7

    # fallback 후에도 _WORKER_LOOP 는 None 유지 (asyncio.run 은 _WORKER_LOOP 미수정)
    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]


def test_run_in_worker_loop_raises_when_called_inside_running_loop() -> None:
    """**codex G.0 P1 #6 fix 회귀 방어**.

    pytest-asyncio / celery_eager mode 처럼 이미 running loop 가 있을 때
    silent fallback 으로 asyncio.run() 호출하면 "cannot be called from a
    running event loop" RuntimeError. silent 대신 명시적 RuntimeError raise
    + 의미 있는 메시지로 디버깅 가능.
    """

    async def _outer() -> None:
        async def _inner() -> int:
            return 99

        # 이미 running loop 안에서 run_in_worker_loop 호출 시도
        _worker_loop.run_in_worker_loop(_inner())

    with pytest.raises(RuntimeError, match="running event loop"):
        asyncio.run(_outer())


def test_shutdown_cancels_pending_tasks_and_closes_loop() -> None:
    """shutdown 이 pending task cancel + loop close. 누락 task 가 worker
    종료를 막지 않음."""
    _worker_loop.init_worker_loop()
    loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]
    assert loop is not None

    # background task 1개 생성 후 shutdown — cancel 됨을 검증.
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def _bg() -> None:
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    async def _start_bg() -> None:
        loop.create_task(_bg())
        # task 가 실제 await sleep 진입할 때까지 대기
        await started.wait()

    _worker_loop.run_in_worker_loop(_start_bg())

    _worker_loop.shutdown_worker_loop()

    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]
    assert loop.is_closed()
    # cancelled.set() 은 shutdown 의 gather 안에서 발생 — 단정 가능
    assert cancelled.is_set()


def test_shutdown_is_idempotent_when_no_loop() -> None:
    """init 미호출 또는 이미 shutdown 된 상태 → no-op (예외 안 남김).

    worker_shutdown signal (master+solo) 이 worker_process_shutdown (child) 후
    중복 호출 가능. idempotent 보장.
    """
    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]
    _worker_loop.shutdown_worker_loop()  # no-op
    _worker_loop.shutdown_worker_loop()  # 2회 연속도 OK


def test_run_in_worker_loop_closes_coro_when_raising_in_running_loop() -> None:
    """**codex G.2 P3 #1 회귀 방어** — running loop guard 가 raise 시 coro.close().

    coro.close() 미호출 시 "coroutine was never awaited" RuntimeWarning 발생.
    pytest-asyncio / celery_eager 환경에서 깔끔한 cleanup 보장.
    """
    closed_coros: list[bool] = []

    async def _inner() -> int:
        return 1  # pragma: no cover — close() 후 await 안 됨

    async def _outer() -> None:
        coro = _inner()
        try:
            _worker_loop.run_in_worker_loop(coro)  # type: ignore[arg-type]
        except RuntimeError:
            # raise 후 coro 가 close 됐는지 검증 — 다시 await 시도하면 immediate result.
            try:
                coro.send(None)
                closed_coros.append(False)  # 아직 안 닫힘
            except StopIteration:
                closed_coros.append(True)  # closed → StopIteration
            except RuntimeError:
                closed_coros.append(True)  # closed
            return

    asyncio.run(_outer())

    assert closed_coros == [True], "coro.close() 미호출 — RuntimeWarning 위험"


def test_shutdown_drains_asyncgens_and_default_executor() -> None:
    """**codex G.2 P2 #3 회귀 방어** — long-lived loop 의 leak surface 차단.

    asyncio.run() 은 cleanup 단계에서 자동으로 shutdown_asyncgens +
    shutdown_default_executor 호출. _WORKER_LOOP 영속 모델은 이걸 명시적으로
    호출 안 하면 누락 → async generator close 못 받고, executor thread 종료
    못 되어 프로세스 종료 시 hang/leak.
    """
    _worker_loop.init_worker_loop()
    loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]
    assert loop is not None

    asyncgen_finalized = asyncio.Event()

    async def _asyncgen():  # type: ignore[no-untyped-def]
        try:
            yield 1
            yield 2
        finally:
            asyncgen_finalized.set()

    async def _consume_once() -> None:
        gen = _asyncgen()
        async for v in gen:
            assert v == 1
            break  # async generator 가 unfinalized 상태로 남음

    _worker_loop.run_in_worker_loop(_consume_once())
    # shutdown 이 asyncgen 의 finally 를 호출 → asyncgen_finalized.set()
    _worker_loop.shutdown_worker_loop()

    assert asyncgen_finalized.is_set(), (
        "shutdown_asyncgens 미호출 — async generator finally 가 실행 안 됨"
    )


def test_shutdown_handles_drain_exception_and_still_closes() -> None:
    """drain phase 의 task gather 가 raise 해도 loop close 보장.

    finally guard 회귀. 사용자 코드의 unhandled exception 이 worker shutdown
    을 막아 zombie state 만들지 않음.
    """
    _worker_loop.init_worker_loop()
    loop = _worker_loop._WORKER_LOOP  # type: ignore[attr-defined]
    assert loop is not None

    async def _exploding_bg() -> None:
        raise RuntimeError("synthetic explosion in shutdown drain")

    async def _start_bg() -> None:
        loop.create_task(_exploding_bg())
        await asyncio.sleep(0)  # task 가 schedule 되도록

    _worker_loop.run_in_worker_loop(_start_bg())

    # shutdown 이 raise 안 함 — 내부 try/except + finally 로 close 보장.
    _worker_loop.shutdown_worker_loop()

    assert _worker_loop._WORKER_LOOP is None  # type: ignore[attr-defined]
    assert loop.is_closed()

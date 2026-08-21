"""Celery dispatch와 backtest worker 수명 계약을 고정한다."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backtest import dependencies as backtest_dependencies
from src.backtest.dispatcher import CeleryTaskDispatcher, NoopTaskDispatcher
from src.optimizer.dispatcher import (
    CeleryOptimizationTaskDispatcher,
    NoopOptimizationTaskDispatcher,
)
from src.stress_test.dispatcher import CeleryStressTaskDispatcher, NoopStressTaskDispatcher
from src.tasks import _worker_loop
from src.tasks import backtest as backtest_module
from src.tasks import optimizer_tasks as optimizer_tasks_module
from src.tasks import stress_test_tasks as stress_test_tasks_module


class _RecordingEngine:
    """dispose() await 횟수를 기록한다."""

    def __init__(self) -> None:
        self.dispose_calls = 0

    async def dispose(self) -> None:
        self.dispose_calls += 1


def _fake_create_worker_engine_and_sm() -> tuple[
    Callable[[], tuple[_RecordingEngine, object]],
    _RecordingEngine,
    MagicMock,
]:
    """engine 수명과 service builder 인자를 관측할 worker factory fake를 만든다."""
    engine = _RecordingEngine()
    session = MagicMock()

    @asynccontextmanager
    async def _session_ctx():
        yield session

    class _SessionMaker:
        def __call__(self):
            return _session_ctx()

    def _factory() -> tuple[_RecordingEngine, object]:
        return engine, _SessionMaker()

    return _factory, engine, session


@pytest.mark.parametrize(
    ("dispatcher", "method_name", "class_name"),
    [
        (NoopTaskDispatcher(), "dispatch_backtest", "NoopTaskDispatcher"),
        (
            NoopOptimizationTaskDispatcher(),
            "dispatch_optimization",
            "NoopOptimizationTaskDispatcher",
        ),
        (
            NoopStressTaskDispatcher(),
            "dispatch_stress_test",
            "NoopStressTaskDispatcher",
        ),
    ],
)
def test_noop_dispatchers_raise_distinguishable_runtime_errors(
    dispatcher: object,
    method_name: str,
    class_name: str,
) -> None:
    """각 worker 방어 dispatcher는 자신의 클래스명을 담아 dispatch를 거부한다."""
    with pytest.raises(RuntimeError, match=class_name):
        getattr(dispatcher, method_name)(uuid4())


@pytest.mark.parametrize(
    ("dispatcher", "method_name", "expected_task"),
    [
        (CeleryTaskDispatcher(), "dispatch_backtest", backtest_module.run_backtest_task),
        (
            CeleryOptimizationTaskDispatcher(),
            "dispatch_optimization",
            optimizer_tasks_module.run_optimization_task,
        ),
        (
            CeleryStressTaskDispatcher(),
            "dispatch_stress_test",
            stress_test_tasks_module.run_stress_test_task,
        ),
    ],
)
def test_celery_dispatchers_enqueue_own_task_with_string_uuid(
    monkeypatch: pytest.MonkeyPatch,
    dispatcher: object,
    method_name: str,
    expected_task: object,
) -> None:
    """각 submit dispatcher는 자기 도메인 task에 문자열 UUID를 넘기고 문자열 ID를 돌려준다."""
    task_delays = {
        backtest_module.run_backtest_task: MagicMock(),
        optimizer_tasks_module.run_optimization_task: MagicMock(),
        stress_test_tasks_module.run_stress_test_task: MagicMock(),
    }
    expected_delay = MagicMock(return_value=SimpleNamespace(id=101))
    task_delays[expected_task] = expected_delay
    for task, delay in task_delays.items():
        monkeypatch.setattr(task, "delay", delay)

    item_id = uuid4()
    result = getattr(dispatcher, method_name)(item_id)

    assert isinstance(result, str)
    assert result == "101"
    expected_delay.assert_called_once_with(str(item_id))
    for task, delay in task_delays.items():
        if task is not expected_task:
            delay.assert_not_called()


def test_run_backtest_task_observes_duration_once_when_worker_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """worker 예외가 밖으로 나가도 histogram observe는 finally에서 한 번 실행된다."""
    observer = MagicMock()

    def _raising_worker_loop(coro: object) -> None:
        coro.close()  # type: ignore[attr-defined]
        raise RuntimeError("worker failed")

    monkeypatch.setattr(_worker_loop, "run_in_worker_loop", _raising_worker_loop)
    monkeypatch.setattr(backtest_module, "qb_backtest_duration_seconds", observer)

    with pytest.raises(RuntimeError, match="worker failed"):
        backtest_module.run_backtest_task.run(str(uuid4()))

    observer.observe.assert_called_once()


def test_run_backtest_task_observes_nonnegative_float_once_when_worker_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정상 worker 경로도 duration histogram을 정확히 한 번 기록한다."""
    observer = MagicMock()

    def _successful_worker_loop(coro: object) -> None:
        coro.close()  # type: ignore[attr-defined]

    monkeypatch.setattr(_worker_loop, "run_in_worker_loop", _successful_worker_loop)
    monkeypatch.setattr(backtest_module, "qb_backtest_duration_seconds", observer)

    backtest_module.run_backtest_task.run(str(uuid4()))

    observer.observe.assert_called_once()
    observed = observer.observe.call_args.args[0]
    assert isinstance(observed, float)
    assert observed >= 0.0


@pytest.mark.asyncio
async def test_execute_passes_opened_session_to_service_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정상 execute는 sm()이 연 session으로 service를 만들고 engine을 한 번 처분한다."""
    factory, engine, session = _fake_create_worker_engine_and_sm()
    service = MagicMock()
    service.run = AsyncMock()
    builder = MagicMock(return_value=service)
    monkeypatch.setattr(backtest_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(backtest_dependencies, "build_backtest_service_for_worker", builder)
    backtest_id = uuid4()

    await backtest_module._execute(backtest_id)

    builder.assert_called_once_with(session)
    service.run.assert_awaited_once_with(backtest_id)
    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_execute_disposes_engine_once_when_service_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """service 실패가 전파돼도 execute finally는 engine을 정확히 한 번 처분한다."""
    factory, engine, session = _fake_create_worker_engine_and_sm()
    service = MagicMock()
    service.run = AsyncMock(side_effect=RuntimeError("service failed"))
    builder = MagicMock(return_value=service)
    monkeypatch.setattr(backtest_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(backtest_dependencies, "build_backtest_service_for_worker", builder)

    with pytest.raises(RuntimeError, match="service failed"):
        await backtest_module._execute(uuid4())

    builder.assert_called_once_with(session)
    service.run.assert_awaited_once()
    assert engine.dispose_calls == 1


def test_reclaim_stale_running_task_returns_worker_loop_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """beat wrapper는 asyncio.run 대신 worker loop 반환값을 변형 없이 전달한다."""
    expected = 7

    async def _reclaim() -> int:
        return 0

    def _worker_loop_result(coro: object) -> int:
        coro.close()  # type: ignore[attr-defined]
        return expected

    worker_loop = MagicMock(side_effect=_worker_loop_result)
    monkeypatch.setattr(backtest_module, "reclaim_stale_running", _reclaim)
    monkeypatch.setattr(_worker_loop, "run_in_worker_loop", worker_loop)

    result = backtest_module.reclaim_stale_running_task.run()

    assert result == expected
    worker_loop.assert_called_once()


def test_backtest_tasks_keep_registration_names_and_no_retries() -> None:
    """worker와 beat가 찾는 backtest task 이름 및 retry 계약을 고정한다."""
    assert backtest_module.run_backtest_task.name == "backtest.run"
    assert backtest_module.run_backtest_task.max_retries == 0
    assert backtest_module.reclaim_stale_running_task.name == "backtest.reclaim_stale"
    assert backtest_module.reclaim_stale_running_task.max_retries == 0

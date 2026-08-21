"""Optimizer·Stress Test worker task의 prefork-safe 수명 계약을 고정한다."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib import import_module
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest


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
    """엔진 수명과 worker service가 받는 session을 관측하는 factory fake를 만든다."""
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


def _module(name: str) -> ModuleType:
    """BL-583 회피를 위해 class 정의 모듈을 patch하기 전에 task 소비 모듈을 적재한다."""
    return import_module(name)


@pytest.mark.parametrize(
    ("task_module_name", "dependency_module_name", "builder_name"),
    [
        (
            "src.tasks.optimizer_tasks",
            "src.optimizer.dependencies",
            "build_optimizer_service_for_worker",
        ),
        (
            "src.tasks.stress_test_tasks",
            "src.stress_test.dependencies",
            "build_stress_test_service_for_worker",
        ),
    ],
)
@pytest.mark.asyncio
async def test_execute_passes_original_uuid_and_session_then_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    dependency_module_name: str,
    builder_name: str,
) -> None:
    """정상 실행은 같은 session·UUID를 service에 넘기고 engine을 한 번 처분한다."""
    task_module = _module(task_module_name)
    dependency_module = _module(dependency_module_name)
    factory, engine, session = _fake_create_worker_engine_and_sm()
    service = MagicMock()
    service.run = AsyncMock()
    builder = MagicMock(return_value=service)
    run_id = uuid4()

    monkeypatch.setattr(task_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(dependency_module, builder_name, builder)

    await task_module._execute(run_id)

    builder.assert_called_once_with(session)
    service.run.assert_awaited_once_with(run_id)
    assert type(service.run.await_args.args[0]) is UUID
    assert engine.dispose_calls == 1


@pytest.mark.parametrize(
    ("task_module_name", "dependency_module_name", "builder_name"),
    [
        (
            "src.tasks.optimizer_tasks",
            "src.optimizer.dependencies",
            "build_optimizer_service_for_worker",
        ),
        (
            "src.tasks.stress_test_tasks",
            "src.stress_test.dependencies",
            "build_stress_test_service_for_worker",
        ),
    ],
)
@pytest.mark.asyncio
async def test_execute_disposes_engine_when_service_raises(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    dependency_module_name: str,
    builder_name: str,
) -> None:
    """service.run 실패가 전파돼도 finally가 engine을 정확히 한 번 처분한다."""
    task_module = _module(task_module_name)
    dependency_module = _module(dependency_module_name)
    factory, engine, _session = _fake_create_worker_engine_and_sm()
    service = MagicMock()
    service.run = AsyncMock(side_effect=RuntimeError("service failed"))

    monkeypatch.setattr(task_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(dependency_module, builder_name, MagicMock(return_value=service))

    with pytest.raises(RuntimeError, match="service failed"):
        await task_module._execute(uuid4())

    service.run.assert_awaited_once()
    assert engine.dispose_calls == 1


@pytest.mark.parametrize(
    ("task_module_name", "dependency_module_name", "builder_name"),
    [
        (
            "src.tasks.optimizer_tasks",
            "src.optimizer.dependencies",
            "build_optimizer_service_for_worker",
        ),
        (
            "src.tasks.stress_test_tasks",
            "src.stress_test.dependencies",
            "build_stress_test_service_for_worker",
        ),
    ],
)
@pytest.mark.asyncio
async def test_execute_creates_fresh_worker_engine_for_each_call(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    dependency_module_name: str,
    builder_name: str,
) -> None:
    """두 실행은 매번 factory를 호출해 module-level engine cache 재도입을 막는다."""
    task_module = _module(task_module_name)
    dependency_module = _module(dependency_module_name)
    first_factory, first_engine, _first_session = _fake_create_worker_engine_and_sm()
    second_factory, second_engine, _second_session = _fake_create_worker_engine_and_sm()
    factory = MagicMock(side_effect=[first_factory(), second_factory()])
    service = MagicMock()
    service.run = AsyncMock()

    monkeypatch.setattr(task_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(dependency_module, builder_name, MagicMock(return_value=service))

    await task_module._execute(uuid4())
    await task_module._execute(uuid4())

    assert factory.call_count == 2
    assert first_engine.dispose_calls == 1
    assert second_engine.dispose_calls == 1


@pytest.mark.parametrize(
    (
        "task_module_name",
        "repository_module_name",
        "repository_name",
        "threshold_name",
        "expected_threshold",
    ),
    [
        (
            "src.tasks.optimizer_tasks",
            "src.optimizer.repository",
            "OptimizationRepository",
            "optimizer_stale_threshold_seconds",
            101,
        ),
        (
            "src.tasks.stress_test_tasks",
            "src.stress_test.repository",
            "StressTestRepository",
            "stress_test_stale_threshold_seconds",
            202,
        ),
    ],
)
@pytest.mark.asyncio
async def test_reclaim_returns_repo_value_commits_and_uses_module_threshold(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    repository_module_name: str,
    repository_name: str,
    threshold_name: str,
    expected_threshold: int,
) -> None:
    """reclaim은 설정별 threshold·UTC now를 넘기고 commit 뒤 repo 결과를 그대로 반환한다."""
    task_module = _module(task_module_name)
    repository_module = _module(repository_module_name)
    config_module = _module("src.core.config")
    factory, engine, session = _fake_create_worker_engine_and_sm()
    reclaimed = object()
    repo = MagicMock()
    repo.reclaim_stale = AsyncMock(return_value=reclaimed)
    repo.commit = AsyncMock()
    repository_factory = MagicMock(return_value=repo)
    settings = SimpleNamespace(
        optimizer_stale_threshold_seconds=101,
        stress_test_stale_threshold_seconds=202,
    )

    monkeypatch.setattr(task_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(repository_module, repository_name, repository_factory)
    monkeypatch.setattr(config_module, "settings", settings)
    before = datetime.now(UTC)

    result = await task_module.reclaim_stale_running()

    after = datetime.now(UTC)
    assert result is reclaimed
    repository_factory.assert_called_once_with(session)
    repo.commit.assert_awaited_once()
    kwargs = repo.reclaim_stale.await_args.kwargs
    assert kwargs["threshold_seconds"] == expected_threshold
    assert getattr(settings, threshold_name) == expected_threshold
    assert kwargs["now"].tzinfo is UTC
    assert before <= kwargs["now"] <= after
    assert engine.dispose_calls == 1


@pytest.mark.parametrize(
    ("task_module_name", "repository_module_name", "repository_name"),
    [
        ("src.tasks.optimizer_tasks", "src.optimizer.repository", "OptimizationRepository"),
        ("src.tasks.stress_test_tasks", "src.stress_test.repository", "StressTestRepository"),
    ],
)
@pytest.mark.asyncio
async def test_reclaim_disposes_engine_when_repository_raises(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    repository_module_name: str,
    repository_name: str,
) -> None:
    """reclaim_stale 예외가 전파돼도 engine dispose finally 계약은 유지한다."""
    task_module = _module(task_module_name)
    repository_module = _module(repository_module_name)
    factory, engine, _session = _fake_create_worker_engine_and_sm()
    repo = MagicMock()
    repo.reclaim_stale = AsyncMock(side_effect=RuntimeError("reclaim failed"))
    repo.commit = AsyncMock()

    monkeypatch.setattr(task_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(repository_module, repository_name, MagicMock(return_value=repo))

    with pytest.raises(RuntimeError, match="reclaim failed"):
        await task_module.reclaim_stale_running()

    repo.reclaim_stale.assert_awaited_once()
    repo.commit.assert_not_awaited()
    assert engine.dispose_calls == 1


@pytest.mark.parametrize(
    ("task_module_name", "task_name"),
    [
        ("src.tasks.optimizer_tasks", "run_optimization_task"),
        ("src.tasks.stress_test_tasks", "run_stress_test_task"),
    ],
)
def test_execute_wrapper_passes_coroutine_to_worker_loop(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    task_name: str,
) -> None:
    """실행 sync wrapper는 asyncio.run 대신 run_in_worker_loop에 coroutine을 한 번 넘긴다."""
    task_module = _module(task_module_name)
    worker_loop_module = _module("src.tasks._worker_loop")
    run_id = uuid4()
    execute = AsyncMock()
    received: list[object] = []

    def _run(coroutine: object) -> object:
        received.append(coroutine)
        coroutine.close()  # type: ignore[union-attr]
        return object()

    monkeypatch.setattr(task_module, "_execute", execute)
    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", _run)

    result = getattr(task_module, task_name).run(str(run_id))

    assert result is None
    execute.assert_called_once_with(run_id)
    assert len(received) == 1
    assert inspect.iscoroutine(received[0])


@pytest.mark.parametrize(
    "task_module_name", ["src.tasks.optimizer_tasks", "src.tasks.stress_test_tasks"]
)
def test_reclaim_wrapper_returns_worker_loop_result(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
) -> None:
    """Beat reclaim wrapper는 run_in_worker_loop에 coroutine을 한 번 넘기고 결과를 그대로 반환한다."""
    task_module = _module(task_module_name)
    worker_loop_module = _module("src.tasks._worker_loop")
    expected = object()
    reclaim = AsyncMock(return_value=expected)
    received: list[object] = []

    def _run(coroutine: object) -> object:
        received.append(coroutine)
        coroutine.close()  # type: ignore[union-attr]
        return expected

    monkeypatch.setattr(task_module, "reclaim_stale_running", reclaim)
    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", _run)

    result = task_module.reclaim_stale_running_task.run()

    assert result is expected
    reclaim.assert_called_once_with()
    assert len(received) == 1
    assert inspect.iscoroutine(received[0])


@pytest.mark.parametrize(
    ("task_module_name", "task_name"),
    [
        ("src.tasks.optimizer_tasks", "run_optimization_task"),
        ("src.tasks.stress_test_tasks", "run_stress_test_task"),
    ],
)
def test_execute_wrapper_rejects_invalid_uuid_before_worker_loop(
    monkeypatch: pytest.MonkeyPatch,
    task_module_name: str,
    task_name: str,
) -> None:
    """잘못된 UUID는 worker loop·engine 생성 전에 ValueError로 종료한다."""
    task_module = _module(task_module_name)
    worker_loop_module = _module("src.tasks._worker_loop")
    run_worker_loop = MagicMock()
    create_engine = MagicMock()

    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", run_worker_loop)
    monkeypatch.setattr(task_module, "create_worker_engine_and_sm", create_engine)

    with pytest.raises(ValueError):
        getattr(task_module, task_name).run("not-a-uuid")

    run_worker_loop.assert_not_called()
    create_engine.assert_not_called()


def test_worker_tasks_keep_celery_registration_and_time_limit_contract() -> None:
    """Beat·worker가 찾는 네 등록 이름과 실행 제한 계약을 고정한다."""
    optimizer_module = _module("src.tasks.optimizer_tasks")
    stress_test_module = _module("src.tasks.stress_test_tasks")

    assert optimizer_module.run_optimization_task.name == "optimizer.run"
    assert optimizer_module.run_optimization_task.max_retries == 0
    assert optimizer_module.run_optimization_task.soft_time_limit == 600
    assert optimizer_module.run_optimization_task.time_limit == 660
    assert optimizer_module.reclaim_stale_running_task.name == "optimizer.reclaim_stale"
    assert optimizer_module.reclaim_stale_running_task.max_retries == 0
    assert stress_test_module.run_stress_test_task.name == "stress_test.run"
    assert stress_test_module.run_stress_test_task.max_retries == 0
    assert stress_test_module.run_stress_test_task.soft_time_limit is None
    assert stress_test_module.run_stress_test_task.time_limit is None
    assert stress_test_module.reclaim_stale_running_task.name == "stress_test.reclaim_stale"
    assert stress_test_module.reclaim_stale_running_task.max_retries == 0

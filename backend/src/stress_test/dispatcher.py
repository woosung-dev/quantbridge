"""StressTaskDispatcher — submit 경로에서 Celery task enqueue.

backtest/dispatcher.py 와 동일 Protocol 패턴. Service 가 src.tasks 를 직접 import
하면 순환 의존이 발생하므로 Dispatcher 로 추상화.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID


class StressTaskDispatcher(Protocol):
    """Stress test task enqueue 인터페이스."""

    def dispatch_stress_test(self, stress_test_id: UUID) -> str:
        """Enqueue stress test task. Returns celery task id."""
        ...


class CeleryStressTaskDispatcher:
    """실 구현 — HTTP submit 경로에서만 사용."""

    def dispatch_stress_test(self, stress_test_id: UUID) -> str:
        """Celery worker 에 stress test task 를 enqueue."""
        from src.tasks.stress_test_tasks import run_stress_test_task  # 지연 import

        async_result = run_stress_test_task.delay(str(stress_test_id))
        return str(async_result.id)


class NoopStressTaskDispatcher:
    """Worker _execute() / 테스트용 — 호출되면 명시적 오류."""

    def dispatch_stress_test(self, stress_test_id: UUID) -> str:
        raise RuntimeError("NoopStressTaskDispatcher must not dispatch")


class FakeStressTaskDispatcher:
    """테스트 전용 — 호출 기록."""

    def __init__(self, task_id: str = "test-stress-task-id") -> None:
        self.task_id = task_id
        self.dispatched: list[UUID] = []

    def dispatch_stress_test(self, stress_test_id: UUID) -> str:
        self.dispatched.append(stress_test_id)
        return self.task_id

"""TaskDispatcher — submit 경로에서 Celery task enqueue.

BacktestService가 src.tasks를 직접 import하면 순환 의존 발생 (tasks가 service를 import).
Dispatcher Protocol로 추상화하고 dependencies.py에서 CeleryTaskDispatcher 주입.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID


class TaskDispatcher(Protocol):
    """Backtest task를 enqueue하는 인터페이스."""

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """Enqueue backtest task. Returns celery task id."""
        ...


class CeleryTaskDispatcher:
    """실 구현 — HTTP submit 경로(dependencies.py)에서만 사용."""

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """Celery worker에 backtest task를 enqueue."""
        from src.tasks.backtest import run_backtest_task  # 지연 import (순환 방지)

        async_result = run_backtest_task.delay(str(backtest_id))
        return str(async_result.id)


class NoopTaskDispatcher:
    """Worker _execute() 내부 / 일부 테스트용.

    dispatch 호출되면 RuntimeError — submit/run 책임 분리 명시.
    """

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """호출되면 항상 오류 발생 — submit과 run 책임 분리 강제."""
        raise RuntimeError("NoopTaskDispatcher must not dispatch")


class FakeTaskDispatcher:
    """테스트 전용 — 고정 task_id 반환 + 호출 기록."""

    def __init__(self, task_id: str = "test-task-id") -> None:
        """
        Args:
            task_id: dispatch_backtest에서 반환할 고정 task ID.
        """
        self.task_id = task_id
        self.dispatched: list[UUID] = []

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """호출 기록하고 고정 task_id 반환."""
        self.dispatched.append(backtest_id)
        return self.task_id

"""TaskDispatcher — submit 경로에서 Celery task enqueue + cancel 경로의 revoke.

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

    def revoke_backtest(self, celery_task_id: str) -> None:
        """실행 중 backtest task를 revoke(terminate=True)한다.

        best-effort 실패 처리(예외 삼킴 + 로그)는 호출자(`BacktestService.cancel`)가 갖는다.
        구현은 예외를 그대로 던진다.
        """
        ...


class CeleryTaskDispatcher:
    """실 구현 — HTTP submit 경로(dependencies.py)에서만 사용."""

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """Celery worker에 backtest task를 enqueue."""
        from src.tasks.backtest import run_backtest_task  # 지연 import (순환 방지)

        async_result = run_backtest_task.delay(str(backtest_id))
        return str(async_result.id)

    def revoke_backtest(self, celery_task_id: str) -> None:
        """Celery에 backtest task revoke(terminate=True)를 요청."""
        from celery.result import (  # type: ignore[import-untyped]  # 지연 import (순환 방지)
            AsyncResult,
        )

        from src.tasks.celery_app import celery_app

        AsyncResult(celery_task_id, app=celery_app).revoke(terminate=True)


class NoopTaskDispatcher:
    """Worker _execute() 내부 / 일부 테스트용.

    dispatch 호출되면 RuntimeError — submit/run 책임 분리 명시.
    """

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """호출되면 항상 오류 발생 — submit과 run 책임 분리 강제."""
        raise RuntimeError("NoopTaskDispatcher must not dispatch")

    def revoke_backtest(self, celery_task_id: str) -> None:
        """호출되면 항상 오류 발생 — worker 경로는 cancel(revoke)을 하지 않는다."""
        raise RuntimeError("NoopTaskDispatcher must not revoke")


class FakeTaskDispatcher:
    """테스트 전용 — 고정 task_id 반환 + 호출 기록."""

    def __init__(self, task_id: str = "test-task-id") -> None:
        """
        Args:
            task_id: dispatch_backtest에서 반환할 고정 task ID.
        """
        self.task_id = task_id
        self.dispatched: list[UUID] = []
        self.revoked: list[str] = []

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """호출 기록하고 고정 task_id 반환."""
        self.dispatched.append(backtest_id)
        return self.task_id

    def revoke_backtest(self, celery_task_id: str) -> None:
        """revoke 요청을 기록만 한다."""
        self.revoked.append(celery_task_id)

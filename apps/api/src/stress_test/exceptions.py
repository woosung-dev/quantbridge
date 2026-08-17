"""stress_test 도메인 예외. src.common.exceptions.AppException 상속."""

from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class StressTestError(AppException):
    """stress_test 도메인 베이스."""

    def __init__(
        self,
        detail: str | None = None,
        *,
        message_public: str | None = None,
        message_internal: str | None = None,
    ) -> None:
        """실행 경로의 public/internal 메시지를 함께 보존한다."""
        super().__init__(message_public or detail)
        self.message_public = self.detail
        self.message_internal = message_internal or self.message_public


class StressTestNotFound(StressTestError):
    """소유자 격리 고려 — 존재하지 않거나 타 사용자 소유 모두 404."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "stress_test_not_found"
    detail = "Stress test not found"


class StressTestStateConflict(StressTestError):
    """상태 전이 허용되지 않음 (예: 실행 중 재실행)."""

    status_code = status.HTTP_409_CONFLICT
    code = "stress_test_state_conflict"
    detail = "Stress test state does not allow this action"


class BacktestNotCompletedForStressTest(StressTestError):
    """참조된 Backtest 가 COMPLETED 상태가 아님 — equity_curve 부재."""

    status_code = status.HTTP_409_CONFLICT
    code = "backtest_not_completed"
    detail = "Referenced backtest is not in COMPLETED state"


class StressTestTaskDispatchError(StressTestError):
    """Celery 태스크 디스패치 실패."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "stress_test_task_dispatch_failed"
    detail = "Failed to dispatch stress test task"

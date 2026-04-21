"""backtest 도메인 예외."""
from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class BacktestError(AppException):
    """backtest 도메인 베이스."""


class BacktestNotFound(BacktestError):
    """소유자 격리 고려 — 존재하지 않거나 타 사용자 소유 모두 404."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "backtest_not_found"
    detail = "Backtest not found"


class BacktestStateConflict(BacktestError):
    """백테스트 상태가 작업을 허용하지 않음 (예: 완료된 백테스트 재실행)."""

    status_code = status.HTTP_409_CONFLICT
    code = "backtest_state_conflict"
    detail = "Backtest state does not allow this action"


class OHLCVFixtureNotFound(BacktestError):
    """백테스트에 필요한 OHLCV 데이터가 없음."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "ohlcv_fixture_not_found"
    detail = "OHLCV fixture not found"


class TaskDispatchError(BacktestError):
    """Celery 태스크 디스패치 실패 (Redis/Celery 상태 문제)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "task_dispatch_failed"
    detail = "Failed to dispatch background task"


class BacktestDuplicateIdempotencyKey(BacktestError):
    """동일 Idempotency-Key로 backtest가 이미 존재함. detail에 existing_id 포함."""

    status_code = status.HTTP_409_CONFLICT
    code = "backtest_idempotency_conflict"
    detail = "Duplicate Idempotency-Key"

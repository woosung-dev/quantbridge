"""strategy 도메인 예외."""
from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException


class StrategyError(AppException):
    """strategy 도메인 베이스."""


class StrategyNotFoundError(StrategyError):
    """소유자 격리 고려 — 존재하지 않거나 타 사용자 소유 모두 404."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "strategy_not_found"
    detail = "Strategy not found"


class StrategyHasBacktests(StrategyError):
    """전략 삭제 시 관련 백테스트가 있으면 409. 아카이브로 대체해야 함."""

    status_code = status.HTTP_409_CONFLICT
    code = "strategy_has_backtests"
    detail = "Strategy has associated backtests. Archive instead of delete."

# Sprint 62 T-1 (BL-350+354) — OptimizerService get/list 손상 row resilience 회귀 test
"""row-level resilience — invalid row 자동 skip + valid only 응답.

Multi-Agent QA 2026-05-17 발견 (★★★ Curious + Casual 공통 P0):
Sprint 50-52 의 retro-incorrect result_jsonb row + Sprint 53-55 의 schema tightening
합집합으로 OptimizerService._to_response Pydantic ValidationError raise → list comprehension
전체 fail → API 500 → FE 가 raw error JSON 본문 노출.

본 fix: list() 내부 row 별 try/except + skip + WARN log + valid items 만 응답.
optimizer-deepen C-min (2026-07-13): 방어를 _to_response_or_none SSOT 로 승격,
get() 도 손상 row 에서 500 대신 404 (OptimizationNotFoundError) — 대칭 회귀 추가.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.optimizer.dispatcher import FakeOptimizationTaskDispatcher
from src.optimizer.exceptions import OptimizationNotFoundError
from src.optimizer.models import (
    OptimizationKind,
    OptimizationRun,
    OptimizationStatus,
)
from src.optimizer.service import OptimizerService


def _make_valid_param_space_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "objective_metric": "sharpe_ratio",
        "direction": "maximize",
        "max_evaluations": 4,
        "parameters": {
            "ema": {"kind": "integer", "min": 10, "max": 20, "step": 10},
            "stop": {"kind": "decimal", "min": "0.5", "max": "1.0", "step": "0.5"},
        },
    }


def _make_run(
    *,
    user_id: UUID,
    param_space: dict[str, Any],
) -> OptimizationRun:
    return OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=uuid4(),
        kind=OptimizationKind.GRID_SEARCH,
        status=OptimizationStatus.COMPLETED,
        param_space=param_space,
    )


def _build_service(repo: AsyncMock) -> OptimizerService:
    return OptimizerService(
        repo=repo,
        backtest_repo=AsyncMock(),
        strategy_repo=AsyncMock(),
        ohlcv_provider=AsyncMock(),
        dispatcher=FakeOptimizationTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_list_returns_valid_items_only_when_some_rows_invalid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """invalid row (param_space schema 위반) 자동 skip + valid 만 응답 + WARN log."""
    user_id = uuid4()
    valid_run = _make_run(user_id=user_id, param_space=_make_valid_param_space_dict())
    # invalid row = param_space 가 ParamSpace schema 와 불일치 (Sprint 50-52 retro pattern)
    invalid_run = _make_run(
        user_id=user_id,
        param_space={"schema_version": 1, "broken_field": "no_required_fields"},
    )

    repo = AsyncMock()
    repo.list_by_user.return_value = (
        [(invalid_run, None), (valid_run, None), (invalid_run, None)],
        3,
    )
    service = _build_service(repo=repo)

    caplog.set_level(logging.WARNING, logger="src.optimizer.service")
    page = await service.list(user_id=user_id, limit=10, offset=0)

    # valid 1건만 응답
    assert len(page.items) == 1
    assert page.items[0].id == valid_run.id
    # total 은 BE repo 가 보고한 그대로 (invalid 도 카운트)
    assert page.total == 3

    # WARN log 2건 (invalid 각각)
    skip_logs = [r for r in caplog.records if "optimizer_run_skip_invalid_schema" in r.getMessage()]
    assert len(skip_logs) == 2


@pytest.mark.asyncio
async def test_get_corrupt_row_raises_not_found_instead_of_500(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """deepen C-min: 손상 row 상세 조회 → ValidationError 500 대신 404 + WARN."""
    user_id = uuid4()
    corrupt_run = _make_run(
        user_id=user_id,
        param_space={"schema_version": 1, "broken_field": "no_required_fields"},
    )

    repo = AsyncMock()
    repo.get_by_id.return_value = (corrupt_run, None)
    service = _build_service(repo=repo)

    caplog.set_level(logging.WARNING, logger="src.optimizer.service")
    with pytest.raises(OptimizationNotFoundError):
        await service.get(corrupt_run.id, user_id=user_id)

    skip_logs = [r for r in caplog.records if "optimizer_run_skip_invalid_schema" in r.getMessage()]
    assert len(skip_logs) == 1


@pytest.mark.asyncio
async def test_get_valid_row_returns_response() -> None:
    """deepen C-min 회귀: 정상 row 는 기존과 동일하게 응답."""
    user_id = uuid4()
    valid_run = _make_run(user_id=user_id, param_space=_make_valid_param_space_dict())

    repo = AsyncMock()
    repo.get_by_id.return_value = (valid_run, None)
    service = _build_service(repo=repo)

    response = await service.get(valid_run.id, user_id=user_id)
    assert response.id == valid_run.id


@pytest.mark.asyncio
async def test_list_returns_all_items_when_all_valid() -> None:
    """모두 valid 시 raise 없이 전체 응답 + WARN log 0."""
    user_id = uuid4()
    runs = [
        _make_run(user_id=user_id, param_space=_make_valid_param_space_dict()) for _ in range(3)
    ]

    repo = AsyncMock()
    repo.list_by_user.return_value = ([(run, None) for run in runs], 3)
    service = _build_service(repo=repo)

    page = await service.list(user_id=user_id, limit=10, offset=0)
    assert len(page.items) == 3
    assert page.total == 3


@pytest.mark.asyncio
async def test_list_returns_empty_when_all_invalid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """모두 invalid 시 raise 안 함 + items 빈 배열 + WARN log 만 누적."""
    user_id = uuid4()
    runs = [_make_run(user_id=user_id, param_space={"broken": True}) for _ in range(2)]

    repo = AsyncMock()
    repo.list_by_user.return_value = ([(run, None) for run in runs], 2)
    service = _build_service(repo=repo)

    caplog.set_level(logging.WARNING, logger="src.optimizer.service")
    page = await service.list(user_id=user_id, limit=10, offset=0)
    assert len(page.items) == 0
    assert page.total == 2

    skip_logs = [r for r in caplog.records if "optimizer_run_skip_invalid_schema" in r.getMessage()]
    assert len(skip_logs) == 2

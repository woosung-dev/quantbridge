"""[BL-414] 스트레스 테스트 목록 행의 대표 지표 — 파생 규칙 + service.list() 배선.

이력 화면이 한 행에 「무엇을 돌렸고 결과가 얼마였나」를 보이려면 목록 응답에 지표가
있어야 한다. 종전 `StressTestSummary` 는 id/backtest_id/kind/status/created_at/
completed_at 뿐이라 결과 열을 그릴 재료가 없었다.

★순수 함수(`headline_metric_from`)만 재면 **service 가 그것을 안 부르는 변이가 red 0** 이다
(AGENTS.md §10 의무 2). 그래서 `list()` 를 통과하는 케이스를 함께 둔다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.serializers import headline_metric_from


def _grid_result(*sharpes: str | None, degenerate_at: int | None = None) -> dict:
    return {
        "param1_name": "fees",
        "param2_name": "slippage",
        "param1_values": ["0.001"],
        "param2_values": ["0.001"],
        "cells": [
            {
                "param1_value": "0.001",
                "param2_value": "0.001",
                "sharpe": s,
                "total_return": "0.01",
                "max_drawdown": "-0.02",
                "num_trades": 3,
                "is_degenerate": i == degenerate_at,
            }
            for i, s in enumerate(sharpes)
        ],
    }


# --- 파생 규칙 -------------------------------------------------------------


def test_monte_carlo_headline_is_mdd_p95() -> None:
    hm = headline_metric_from(
        StressTestKind.MONTE_CARLO,
        StressTestStatus.COMPLETED,
        {"max_drawdown_p95": "-0.1234", "samples": 1000},
    )
    assert hm is not None
    assert hm.key == "max_drawdown_p95"
    # 저장된 원문 그대로 — 반올림·포맷은 화면 몫이다.
    assert hm.value == "-0.1234"


def test_walk_forward_headline_keeps_infinity_literal() -> None:
    """`degradation_ratio` 는 `Decimal("Infinity")` → `"Infinity"` 로 저장된다.

    여기서 None 으로 뭉개면 「열화 무한대」와 「지표 없음」이 화면에서 같아진다.
    """
    hm = headline_metric_from(
        StressTestKind.WALK_FORWARD,
        StressTestStatus.COMPLETED,
        {"degradation_ratio": "Infinity", "folds": []},
    )
    assert hm is not None
    assert hm.key == "degradation_ratio"
    assert hm.value == "Infinity"


def test_grid_headline_is_worst_non_degenerate_sharpe() -> None:
    """최저 sharpe — degenerate cell 과 sharpe=None cell 은 후보에서 뺀다."""
    hm = headline_metric_from(
        StressTestKind.COST_ASSUMPTION_SENSITIVITY,
        StressTestStatus.COMPLETED,
        _grid_result("1.5", None, "-9.99", "0.3", degenerate_at=2),
    )
    assert hm is not None
    assert hm.key == "worst_cell_sharpe"
    assert hm.value == "0.3"


def test_grid_headline_is_none_when_every_cell_is_unusable() -> None:
    """전 cell 이 degenerate/None 이면 지표가 없다 — 0 이 아니다 ([BL-465])."""
    assert (
        headline_metric_from(
            StressTestKind.PARAM_STABILITY,
            StressTestStatus.COMPLETED,
            _grid_result(None, "1.0", degenerate_at=1),
        )
        is None
    )


@pytest.mark.parametrize(
    "status",
    [StressTestStatus.QUEUED, StressTestStatus.RUNNING, StressTestStatus.FAILED],
)
def test_non_completed_has_no_headline(status: StressTestStatus) -> None:
    """FAILED 는 result 가 남아 있어도 지표를 내지 않는다 — 실패한 실행의 숫자는 거짓이다."""
    assert (
        headline_metric_from(StressTestKind.MONTE_CARLO, status, {"max_drawdown_p95": "-0.1"})
        is None
    )


# --- service.list() 배선 ---------------------------------------------------


def _row(kind: StressTestKind, status: StressTestStatus, result: dict | None) -> StressTest:
    return StressTest(
        id=uuid4(),
        user_id=uuid4(),
        backtest_id=uuid4(),
        kind=kind,
        status=status,
        params={},
        result=result,
        created_at=datetime(2026, 8, 17, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_list_attaches_headline_metric_per_row() -> None:
    """목록 응답의 각 행이 자기 kind 의 지표를 갖는다 (실패 행은 None)."""
    from src.stress_test.service import StressTestService

    rows = [
        _row(
            StressTestKind.MONTE_CARLO,
            StressTestStatus.COMPLETED,
            {"max_drawdown_p95": "-0.42"},
        ),
        _row(StressTestKind.WALK_FORWARD, StressTestStatus.FAILED, None),
    ]
    repo = AsyncMock()
    repo.list_by_user.return_value = (rows, 2)
    service = StressTestService(
        repo=repo,
        backtest_repo=AsyncMock(),
        strategy_repo=AsyncMock(),
        ohlcv_provider=AsyncMock(),
        dispatcher=AsyncMock(),
    )

    page = await service.list(user_id=uuid4(), limit=20, offset=0)

    assert page.total == 2
    assert page.items[0].headline_metric is not None
    assert page.items[0].headline_metric.key == "max_drawdown_p95"
    assert page.items[0].headline_metric.value == "-0.42"
    assert page.items[1].headline_metric is None

"""전략 목록의 파라미터 수와 수명주기 파생 필드 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.schemas import StrategyLifecycle
from src.strategy.service import StrategyService


def _strategy(source: str) -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="oracle",
        pine_source=source,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source",
    [
        '//@version=5\nstrategy("empty")',
        '//@version=5\nstrategy("input(")',
        """//@version=5
strategy("input title")
length = input.int(14, title="input.float(")
""",
        """//@version=5
strategy("mixed")
length = input.int(14)
factor = input.float(2.5)
enabled = input.bool(true)
title = input.string("x")
""",
        """//@version=5
strategy("comments")
// input.int(99)
length = input.int(14) // input.float(1.2)
""",
    ],
)
async def test_param_count_matches_ast_input_oracle(source: str) -> None:
    strategy = _strategy(source)
    repo = AsyncMock()
    repo.list_by_owner.return_value = ([strategy], 1)
    backtest_repo = AsyncMock()
    backtest_repo.count_completed_by_strategy_ids.return_value = {}
    backtest_repo.latest_completed_by_strategy_ids.return_value = {}

    result = await StrategyService(repo, backtest_repo).list(
        owner_id=strategy.user_id,
        limit=20,
        offset=0,
        parse_status=None,
        is_archived=False,
    )

    assert result.items[0].param_count == len(extract_content(source).inputs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("completed_count", "has_active", "expected"),
    [
        (0, False, StrategyLifecycle.draft),
        (1, False, StrategyLifecycle.validated),
        (0, True, StrategyLifecycle.deployed),
        (3, True, StrategyLifecycle.deployed),
    ],
)
async def test_lifecycle_uses_active_sessions_before_backtest_count(
    completed_count: int,
    has_active: bool,
    expected: StrategyLifecycle,
) -> None:
    strategy = _strategy('//@version=5\nstrategy("lifecycle")')
    active_strategy_ids = {strategy.id} if has_active else set()
    repo = AsyncMock()
    repo.list_by_owner.return_value = ([strategy], 1)
    backtest_repo = AsyncMock()
    backtest_repo.count_completed_by_strategy_ids.return_value = {strategy.id: completed_count}
    backtest_repo.latest_completed_by_strategy_ids.return_value = {}
    live_repo = AsyncMock()
    live_repo.list_active_strategy_ids.return_value = active_strategy_ids

    result = await StrategyService(
        repo,
        backtest_repo,
        live_session_repo=live_repo,
    ).list(
        owner_id=strategy.user_id,
        limit=20,
        offset=0,
        parse_status=None,
        is_archived=False,
    )

    assert result.items[0].lifecycle == expected

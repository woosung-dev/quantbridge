"""Sprint 16 BL-010 — Backtest mutation commit-spy (LESSON-019 backfill).

Backtest service mutation 마다 repo.commit() 호출 강제. db_session false-positive
회피 — AsyncMock spy 가 Sprint 6 broken bug 패턴 직접 검증.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backtest.models import Backtest, BacktestStatus
from src.backtest.schemas import CreateBacktestRequest
from src.strategy.models import ParseStatus, PineVersion, Strategy


def _make_strategy() -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="t",
        pine_source="//@version=5\nstrategy('t')\n",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )


def _make_request(strategy_id):
    return CreateBacktestRequest(
        strategy_id=strategy_id,
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )


@pytest.mark.asyncio
async def test_submit_calls_repo_commit() -> None:
    """LESSON-019 spy: submit() (no idempotency) 가 repo.commit() 호출 강제."""
    from src.backtest.service import BacktestService

    repo = AsyncMock()
    repo.create = AsyncMock(return_value=None)

    strategy = _make_strategy()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    ohlcv_provider = AsyncMock()

    dispatcher = AsyncMock()
    dispatcher.dispatch_backtest = lambda _: "task-id-123"  # sync method

    svc = BacktestService(
        repo=repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=ohlcv_provider,
        dispatcher=dispatcher,
    )

    req = _make_request(strategy.id)
    await svc.submit(req, user_id=strategy.user_id, idempotency_key=None)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← LESSON-019


@pytest.mark.asyncio
async def test_cancel_winner_calls_repo_commit() -> None:
    """LESSON-019 spy: cancel() winner (request_cancel rows=1) 가 repo.commit() 호출."""
    from src.backtest.service import BacktestService

    bt = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.RUNNING,
        celery_task_id=None,  # revoke 분기 skip — 더 단순
    )

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=bt)
    repo.request_cancel = AsyncMock(return_value=1)  # winner

    svc = BacktestService(
        repo=repo,
        strategy_repo=AsyncMock(),
        ohlcv_provider=AsyncMock(),
        dispatcher=AsyncMock(),
    )

    await svc.cancel(bt.id, user_id=bt.user_id)

    repo.request_cancel.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_terminal_calls_repo_commit() -> None:
    """LESSON-019 spy: delete() (terminal status) 가 repo.commit() 호출 강제."""
    from src.backtest.service import BacktestService

    bt = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
    )

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=bt)
    repo.delete = AsyncMock(return_value=None)

    svc = BacktestService(
        repo=repo,
        strategy_repo=AsyncMock(),
        ohlcv_provider=AsyncMock(),
        dispatcher=AsyncMock(),
    )

    await svc.delete(bt.id, user_id=bt.user_id)

    repo.delete.assert_awaited_once()
    repo.commit.assert_awaited_once()

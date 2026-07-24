# 전략별 최신 완료 백테스트 투영 쿼리를 검증하는 테스트.
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import BacktestStatus
from src.backtest.repository import BacktestRepository
from tests.backtest.test_repository import _seed_bt


@pytest.mark.asyncio
async def test_latest_completed_by_strategy_ids_returns_one_latest_completed_row(
    db_session: AsyncSession,
) -> None:
    oldest = await _seed_bt(db_session, BacktestStatus.COMPLETED)
    newest = await _seed_bt(db_session, BacktestStatus.COMPLETED)
    non_completed = await _seed_bt(db_session, BacktestStatus.RUNNING)
    other = await _seed_bt(db_session, BacktestStatus.COMPLETED)
    newest.strategy_id = oldest.strategy_id
    non_completed.strategy_id = oldest.strategy_id
    oldest.completed_at = datetime(2024, 1, 1, tzinfo=UTC)
    newest.completed_at = oldest.completed_at + timedelta(hours=1)
    non_completed.completed_at = newest.completed_at + timedelta(hours=1)
    await db_session.flush()

    result = await BacktestRepository(db_session).latest_completed_by_strategy_ids(
        [oldest.strategy_id, other.strategy_id]
    )

    assert result[oldest.strategy_id].id == newest.id
    assert result[other.strategy_id].id == other.id
    assert set(result) == {oldest.strategy_id, other.strategy_id}


@pytest.mark.asyncio
async def test_latest_completed_by_strategy_ids_empty_input(db_session: AsyncSession) -> None:
    assert await BacktestRepository(db_session).latest_completed_by_strategy_ids([]) == {}

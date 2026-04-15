"""StrategyService.delete() unit-level — IntegrityError translation 검증."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.exc import IntegrityError

from src.strategy.exceptions import StrategyHasBacktests
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.service import StrategyService


def _make_strategy(owner_id, strategy_id=None):
    return Strategy(
        id=strategy_id or uuid4(),
        user_id=owner_id,
        name="t",
        pine_source="//@version=5\nstrategy('t')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )


@pytest.mark.asyncio
async def test_delete_translates_fk_violation_to_strategy_has_backtests() -> None:
    """IntegrityError(orig=ForeignKeyViolationError) → StrategyHasBacktests."""
    owner_id = uuid4()
    strategy = _make_strategy(owner_id)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_owner.return_value = strategy

    # asyncpg ForeignKeyViolationError를 orig으로 갖는 IntegrityError
    fk_err = asyncpg.exceptions.ForeignKeyViolationError("fk violation")
    mock_repo.delete.side_effect = IntegrityError(
        statement="DELETE", params=None, orig=fk_err
    )

    mock_backtest_repo = AsyncMock()
    # TOCTOU race: 선조회는 False이지만 DB-level FK가 발화
    mock_backtest_repo.exists_for_strategy.return_value = False

    service = StrategyService(repo=mock_repo, backtest_repo=mock_backtest_repo)

    with pytest.raises(StrategyHasBacktests):
        await service.delete(strategy_id=strategy.id, owner_id=owner_id)

    # rollback이 호출됐는지 검증
    mock_repo.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_other_integrity_error_propagates() -> None:
    """non-FK IntegrityError는 그대로 propagate (StrategyHasBacktests로 변환 X)."""
    owner_id = uuid4()
    strategy = _make_strategy(owner_id)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_owner.return_value = strategy

    # Unique violation 같은 다른 IntegrityError
    unique_err = asyncpg.exceptions.UniqueViolationError("unique violation")
    mock_repo.delete.side_effect = IntegrityError(
        statement="DELETE", params=None, orig=unique_err
    )

    mock_backtest_repo = AsyncMock()
    mock_backtest_repo.exists_for_strategy.return_value = False

    service = StrategyService(repo=mock_repo, backtest_repo=mock_backtest_repo)

    # IntegrityError 그대로 propagate (StrategyHasBacktests 아님)
    with pytest.raises(IntegrityError):
        await service.delete(strategy_id=strategy.id, owner_id=owner_id)


@pytest.mark.asyncio
async def test_delete_pre_check_skips_when_no_backtest_repo() -> None:
    """backtest_repo=None (Sprint 3 호환) — 선조회 스킵, FK는 DB가 보장."""
    owner_id = uuid4()
    strategy = _make_strategy(owner_id)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_owner.return_value = strategy

    service = StrategyService(repo=mock_repo, backtest_repo=None)

    await service.delete(strategy_id=strategy.id, owner_id=owner_id)

    mock_repo.delete.assert_awaited_once()
    mock_repo.commit.assert_awaited_once()

"""StrategyService 단위 — repository mock + 실 parser."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest
from src.strategy.service import StrategyService


@pytest.fixture
def repo_mock():
    return AsyncMock()


@pytest.fixture
def service(repo_mock):
    return StrategyService(repo_mock)


_OK_SOURCE = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""

# pine_v2 마이그레이션: 구 엔진 'unsupported' 분류는 제거됨.
# parse 실패 시나리오로 malformed 소스 사용 → status=error + parse_errors 수집.
_UNSUPPORTED_SOURCE = "@@@ this is not pine $$$"


@pytest.mark.asyncio
async def test_parse_preview_ok(service):
    result = await service.parse_preview(_OK_SOURCE)
    assert result.status == ParseStatus.ok
    assert result.pine_version == PineVersion.v5


@pytest.mark.asyncio
async def test_parse_preview_unsupported_returns_without_raising(service):
    result = await service.parse_preview(_UNSUPPORTED_SOURCE)
    assert result.status in (ParseStatus.unsupported, ParseStatus.error)
    assert result.errors


@pytest.mark.asyncio
async def test_create_records_parse_status(service, repo_mock):
    owner_id = uuid4()
    req = CreateStrategyRequest(name="x", pine_source=_OK_SOURCE)
    repo_mock.create.side_effect = lambda s: s  # return 그대로

    result = await service.create(req, owner_id=owner_id)

    repo_mock.create.assert_awaited_once()
    repo_mock.commit.assert_awaited_once()
    assert result.parse_status == ParseStatus.ok


@pytest.mark.asyncio
async def test_create_stores_even_when_unsupported(service, repo_mock):
    owner_id = uuid4()
    req = CreateStrategyRequest(name="x", pine_source=_UNSUPPORTED_SOURCE)
    repo_mock.create.side_effect = lambda s: s

    result = await service.create(req, owner_id=owner_id)

    repo_mock.create.assert_awaited_once()
    assert result.parse_status in (ParseStatus.unsupported, ParseStatus.error)
    assert result.parse_errors is not None


@pytest.mark.asyncio
async def test_get_by_id_not_owned_raises_not_found(service, repo_mock):
    repo_mock.find_by_id_and_owner.return_value = None
    with pytest.raises(StrategyNotFoundError):
        await service.get(strategy_id=uuid4(), owner_id=uuid4())


@pytest.mark.asyncio
async def test_list_adds_completed_backtest_counts(repo_mock):
    owner_id = uuid4()
    counted = Strategy(
        id=uuid4(),
        user_id=owner_id,
        name="counted",
        pine_source=_OK_SOURCE,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    empty = Strategy(
        id=uuid4(),
        user_id=owner_id,
        name="empty",
        pine_source=_OK_SOURCE,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    repo_mock.list_by_owner.return_value = ([counted, empty], 2)
    backtest_repo = AsyncMock()
    backtest_repo.count_completed_by_strategy_ids.return_value = {counted.id: 3}
    backtest_repo.latest_completed_by_strategy_ids.return_value = {
        counted.id: SimpleNamespace(
            id=uuid4(),
            completed_at=datetime(2024, 1, 1, tzinfo=UTC),
            metrics={"total_return": "0.1", "num_trades": 2},
        )
    }

    result = await StrategyService(repo_mock, backtest_repo).list(
        owner_id=owner_id,
        limit=20,
        offset=0,
        parse_status=None,
        is_archived=False,
    )

    assert [item.backtest_count for item in result.items] == [3, 0]
    backtest_repo.count_completed_by_strategy_ids.assert_awaited_once_with([counted.id, empty.id])
    backtest_repo.latest_completed_by_strategy_ids.assert_awaited_once_with([counted.id, empty.id])
    assert result.items[0].latest_backtest is not None
    assert result.items[0].latest_backtest.metrics is not None
    assert result.items[0].latest_backtest.metrics.total_return == Decimal("0.1")
    assert result.items[1].latest_backtest is None


@pytest.mark.asyncio
async def test_update_reparses_when_pine_source_changed(service, repo_mock):
    owner_id = uuid4()
    existing = Strategy(
        id=uuid4(),
        user_id=owner_id,
        name="x",
        pine_source="old",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    repo_mock.find_by_id_and_owner.return_value = existing
    repo_mock.update.side_effect = lambda s: s

    req = UpdateStrategyRequest(pine_source=_UNSUPPORTED_SOURCE)
    result = await service.update(strategy_id=existing.id, owner_id=owner_id, data=req)
    assert result.parse_status in (ParseStatus.unsupported, ParseStatus.error)


@pytest.mark.asyncio
async def test_delete_when_not_owned_raises(service, repo_mock):
    repo_mock.find_by_id_and_owner.return_value = None
    with pytest.raises(StrategyNotFoundError):
        await service.delete(strategy_id=uuid4(), owner_id=uuid4())

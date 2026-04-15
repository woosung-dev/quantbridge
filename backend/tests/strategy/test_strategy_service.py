"""StrategyService 단위 — repository mock + 실 parser."""
from __future__ import annotations

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

_UNSUPPORTED_SOURCE = """//@version=5
strategy("no")
x = request.security(syminfo.tickerid, "1D", close)
"""


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
    result = await service.update(
        strategy_id=existing.id, owner_id=owner_id, data=req
    )
    assert result.parse_status in (ParseStatus.unsupported, ParseStatus.error)


@pytest.mark.asyncio
async def test_delete_when_not_owned_raises(service, repo_mock):
    repo_mock.find_by_id_and_owner.return_value = None
    with pytest.raises(StrategyNotFoundError):
        await service.delete(strategy_id=uuid4(), owner_id=uuid4())

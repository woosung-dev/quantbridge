"""Sprint 7d — Strategy 생성/수정 시 trading_sessions 필드 round-trip."""
from __future__ import annotations

import pytest

from src.auth.models import User
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest


async def _svc(db_session):
    from src.backtest.repository import BacktestRepository
    from src.strategy.repository import StrategyRepository
    from src.strategy.service import StrategyService

    return StrategyService(
        repo=StrategyRepository(db_session),
        backtest_repo=BacktestRepository(db_session),
    )


async def test_create_strategy_persists_trading_sessions(db_session, authed_user: User):
    svc = await _svc(db_session)
    req = CreateStrategyRequest(
        name="S1",
        pine_source="//@version=5\nstrategy('x')",
        trading_sessions=["asia", "london"],
    )
    saved = await svc.create(req, owner_id=authed_user.id)

    fetched = await svc.get(strategy_id=saved.id, owner_id=authed_user.id)
    assert fetched.trading_sessions == ["asia", "london"]


async def test_create_strategy_default_sessions_is_empty(db_session, authed_user: User):
    svc = await _svc(db_session)
    req = CreateStrategyRequest(
        name="S2",
        pine_source="//@version=5\nstrategy('x')",
    )
    saved = await svc.create(req, owner_id=authed_user.id)
    fetched = await svc.get(strategy_id=saved.id, owner_id=authed_user.id)
    assert fetched.trading_sessions == []


async def test_update_strategy_replaces_trading_sessions(db_session, authed_user: User):
    svc = await _svc(db_session)
    req = CreateStrategyRequest(
        name="S3",
        pine_source="//@version=5\nstrategy('x')",
        trading_sessions=["asia"],
    )
    saved = await svc.create(req, owner_id=authed_user.id)

    upd = UpdateStrategyRequest(trading_sessions=["ny"])
    await svc.update(strategy_id=saved.id, owner_id=authed_user.id, data=upd)

    fetched = await svc.get(strategy_id=saved.id, owner_id=authed_user.id)
    assert fetched.trading_sessions == ["ny"]


def test_create_request_rejects_unknown_session_name():
    with pytest.raises(ValueError):
        CreateStrategyRequest(
            name="bad",
            pine_source="//@version=5\nstrategy('x')",
            trading_sessions=["tokyo"],
        )


def test_update_request_rejects_unknown_session_name():
    with pytest.raises(ValueError):
        UpdateStrategyRequest(trading_sessions=["bogus"])


def test_update_request_allows_none_trading_sessions():
    """None means "no change"; empty list means "24h"."""
    u = UpdateStrategyRequest(trading_sessions=None)
    assert u.trading_sessions is None

    u2 = UpdateStrategyRequest(trading_sessions=[])
    assert u2.trading_sessions == []

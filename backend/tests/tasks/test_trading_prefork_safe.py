"""Sprint 17 Phase C — tasks/trading.py prefork-safe 회귀 방어.

codex G.0 P1 #1 (격상): tasks/trading.py 의 module-level _worker_engine 캐시도
orphan_scanner 와 동일 silent fail 패턴. dogfood Day 5 사용자 주문 1건 시
broker side effect (실제 거래소 주문) ↔ DB 상태 분기 위험.

Fix: per-call create_worker_engine_and_sm() + finally engine.dispose() (backtest.py:31 mirror).
- _async_execute: per-call engine + finally dispose
- _async_fetch_order_status: per-call engine + finally dispose
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


class _RecordingEngine:
    def __init__(self) -> None:
        self.dispose_calls = 0

    async def dispose(self) -> None:
        self.dispose_calls += 1


def _fake_create_worker_engine_and_sm(
    *, order_mock=None
) -> tuple[Callable[[], tuple[_RecordingEngine, object]], _RecordingEngine]:
    """create_worker_engine_and_sm mock for trading task tests."""
    engine = _RecordingEngine()

    @asynccontextmanager
    async def _session_ctx():
        session_mock = MagicMock()
        session_mock.get = AsyncMock(return_value=None)
        session_mock.commit = AsyncMock()
        yield session_mock

    class _SM:
        def __call__(self):
            return _session_ctx()

    def _factory():
        return engine, _SM()

    return _factory, engine


# -------------------------------------------------------------------------
# Phase C-1: _async_execute
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_execute_calls_create_worker_engine_and_sm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase C — _async_execute 가 create_worker_engine_and_sm() 호출."""
    import src.tasks.trading as trading_mod
    from src.trading.exceptions import OrderNotFound

    factory, _engine = _fake_create_worker_engine_and_sm()
    call_count = {"n": 0}

    def _spy_factory():
        call_count["n"] += 1
        return factory()

    monkeypatch.setattr(trading_mod, "create_worker_engine_and_sm", _spy_factory)

    # repo.get_by_id None → OrderNotFound — engine.dispose 후 raise
    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=None)
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo_mock)

    with pytest.raises(OrderNotFound):
        await trading_mod._async_execute(uuid4())

    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_async_execute_disposes_engine_on_finally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase C — _async_execute 가 정상/raise 모두 engine.dispose() 호출."""
    import src.tasks.trading as trading_mod
    from src.trading.exceptions import OrderNotFound

    factory, engine = _fake_create_worker_engine_and_sm()
    monkeypatch.setattr(trading_mod, "create_worker_engine_and_sm", factory)

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=None)
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo_mock)

    with pytest.raises(OrderNotFound):
        await trading_mod._async_execute(uuid4())

    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_async_execute_disposes_engine_on_runtime_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase C — _async_execute 가 unexpected exception 시에도 dispose."""
    import src.tasks.trading as trading_mod

    factory, engine = _fake_create_worker_engine_and_sm()
    monkeypatch.setattr(trading_mod, "create_worker_engine_and_sm", factory)

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(side_effect=RuntimeError("db kaput"))
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo_mock)

    with pytest.raises(RuntimeError, match="db kaput"):
        await trading_mod._async_execute(uuid4())

    assert engine.dispose_calls == 1


# -------------------------------------------------------------------------
# Phase C-2: _async_fetch_order_status
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_fetch_order_status_calls_create_worker_engine_and_sm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase C — _async_fetch_order_status 가 create_worker_engine_and_sm() 호출."""
    import src.tasks.trading as trading_mod

    factory, _engine = _fake_create_worker_engine_and_sm()
    call_count = {"n": 0}

    def _spy_factory():
        call_count["n"] += 1
        return factory()

    monkeypatch.setattr(trading_mod, "create_worker_engine_and_sm", _spy_factory)

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=None)  # not_found path
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo_mock)

    result = await trading_mod._async_fetch_order_status(uuid4(), 1)
    assert result["skipped"] == "not_found"
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_async_fetch_order_status_disposes_engine_on_finally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase C — _async_fetch_order_status 정상 종료 시 dispose."""
    import src.tasks.trading as trading_mod

    factory, engine = _fake_create_worker_engine_and_sm()
    monkeypatch.setattr(trading_mod, "create_worker_engine_and_sm", factory)

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(return_value=None)
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo_mock)

    await trading_mod._async_fetch_order_status(uuid4(), 1)
    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_async_fetch_order_status_disposes_engine_on_runtime_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase C — _async_fetch_order_status raise 시에도 dispose."""
    import src.tasks.trading as trading_mod

    factory, engine = _fake_create_worker_engine_and_sm()
    monkeypatch.setattr(trading_mod, "create_worker_engine_and_sm", factory)

    repo_mock = MagicMock()
    repo_mock.get_by_id = AsyncMock(side_effect=RuntimeError("query kaput"))
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo_mock)

    with pytest.raises(RuntimeError, match="query kaput"):
        await trading_mod._async_fetch_order_status(uuid4(), 1)
    assert engine.dispose_calls == 1


# -------------------------------------------------------------------------
# Phase C-3: module-level cache 잔존 차단
# -------------------------------------------------------------------------


def test_module_no_global_worker_engine_attribute() -> None:
    """Phase C — module-level _worker_engine / _sessionmaker_cache 잔존 차단.

    회귀 방어: refactor 후 누군가 lazy singleton 다시 도입 시 fail.
    """
    import src.tasks.trading as trading_mod

    assert not hasattr(trading_mod, "_worker_engine"), (
        "module-level _worker_engine 제거 필수 — codex G.0 P1 #1 격상"
    )
    assert not hasattr(trading_mod, "_sessionmaker_cache"), (
        "module-level _sessionmaker_cache 제거 필수"
    )
    assert hasattr(trading_mod, "create_worker_engine_and_sm"), (
        "create_worker_engine_and_sm helper 가 trading_mod 에 존재해야 함"
    )

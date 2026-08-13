"""Sprint 17 Phase A — orphan_scanner prefork-safe 회귀 방어.

Phase 0 라이브 검증 (2026-05-02): 6h 동안 scan_stuck_orders 141/141 fail
(asyncpg InterfaceError) — module-level cached AsyncEngine + Celery prefork
asyncio.run() 새 loop binding mismatch.

Fix: per-call create_worker_engine_and_sm() + finally engine.dispose() (backtest.py:31 mirror).

본 test 는 mock 단위로:
- create_worker_engine_and_sm 호출 1회/per task 검증
- engine.dispose() finally await 검증 (정상 + 예외 path)
- module-level _worker_engine 잔존 차단

real DB integration 회귀는 Phase D 의 test_prefork_smoke_integration.py.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


class _RecordingEngine:
    """dispose() await 기록."""

    def __init__(self) -> None:
        self.dispose_calls = 0

    async def dispose(self) -> None:
        self.dispose_calls += 1


def _fake_create_worker_engine_and_sm() -> tuple[
    Callable[[], tuple[_RecordingEngine, object]],
    _RecordingEngine,
    dict[str, AsyncMock],
]:
    """create_worker_engine_and_sm mock.

    Returns:
        (factory, engine, repo_methods) — factory() 는 (engine, sm) tuple,
        engine 의 dispose 는 호출 카운트 누적, repo_methods 는 OrderRepository
        mock 의 list_stuck_* AsyncMock dict.
    """
    engine = _RecordingEngine()

    repo_methods = {
        "list_stuck_pending": AsyncMock(return_value=[]),
        "list_stuck_submitted": AsyncMock(return_value=[]),
        "list_stuck_submission_interrupted": AsyncMock(return_value=[]),
    }

    @asynccontextmanager
    async def _session_ctx():
        yield MagicMock()

    class _SM:
        def __call__(self):
            return _session_ctx()

    def _factory():
        return engine, _SM()

    return _factory, engine, repo_methods


@pytest.mark.asyncio
async def test_async_scan_stuck_orders_calls_create_worker_engine_and_sm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase A — _async_scan_stuck_orders 가 create_worker_engine_and_sm() 호출."""
    import src.tasks.orphan_scanner as scanner_mod

    factory, _engine, repo_methods = _fake_create_worker_engine_and_sm()
    call_count = {"n": 0}

    def _spy_factory():
        call_count["n"] += 1
        return factory()

    monkeypatch.setattr(scanner_mod, "create_worker_engine_and_sm", _spy_factory)

    repo_mock = MagicMock(**repo_methods)
    monkeypatch.setattr(scanner_mod, "OrderRepository", lambda _session: repo_mock)

    pool_mock = MagicMock()
    pool_mock.set = AsyncMock(return_value=True)
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: pool_mock)

    await scanner_mod._async_scan_stuck_orders()

    assert call_count["n"] == 1, "create_worker_engine_and_sm 가 task 1회 호출"


@pytest.mark.asyncio
async def test_async_scan_stuck_orders_disposes_engine_on_finally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase A — 정상 path 에서도 engine.dispose() 호출."""
    import src.tasks.orphan_scanner as scanner_mod

    factory, engine, repo_methods = _fake_create_worker_engine_and_sm()

    monkeypatch.setattr(scanner_mod, "create_worker_engine_and_sm", factory)
    repo_mock = MagicMock(**repo_methods)
    monkeypatch.setattr(scanner_mod, "OrderRepository", lambda _session: repo_mock)

    pool_mock = MagicMock()
    pool_mock.set = AsyncMock(return_value=True)
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: pool_mock)

    await scanner_mod._async_scan_stuck_orders()

    assert engine.dispose_calls == 1, "engine.dispose() 정상 종료 시 1회 await"


@pytest.mark.asyncio
async def test_async_scan_stuck_orders_disposes_engine_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase A — list_stuck_pending 예외 시에도 engine.dispose() finally 호출."""
    import src.tasks.orphan_scanner as scanner_mod

    factory, engine, _ = _fake_create_worker_engine_and_sm()
    monkeypatch.setattr(scanner_mod, "create_worker_engine_and_sm", factory)

    repo_mock = MagicMock()
    repo_mock.list_stuck_pending = AsyncMock(side_effect=RuntimeError("boom"))
    repo_mock.list_stuck_submitted = AsyncMock(return_value=[])
    repo_mock.list_stuck_submission_interrupted = AsyncMock(return_value=[])
    monkeypatch.setattr(scanner_mod, "OrderRepository", lambda _session: repo_mock)

    pool_mock = MagicMock()
    pool_mock.set = AsyncMock(return_value=True)
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: pool_mock)

    with pytest.raises(RuntimeError, match="boom"):
        await scanner_mod._async_scan_stuck_orders()

    assert engine.dispose_calls == 1, "예외 path 에서도 engine.dispose() finally 호출"


def test_module_no_global_worker_engine_attribute() -> None:
    """Phase A — module-level _worker_engine / _sessionmaker_cache 잔존 차단.

    회귀 방어: refactor 후 누군가 lazy singleton 다시 도입 시 이 test 가 fail.
    """
    import src.tasks.orphan_scanner as scanner_mod

    assert not hasattr(scanner_mod, "_worker_engine"), (
        "module-level _worker_engine 제거 필수 — Phase 0 라이브 141/141 fail 의 root cause"
    )
    assert not hasattr(scanner_mod, "_sessionmaker_cache"), (
        "module-level _sessionmaker_cache 제거 필수"
    )
    assert hasattr(scanner_mod, "create_worker_engine_and_sm"), (
        "create_worker_engine_and_sm helper 가 module 에 존재해야 함 (backtest.py mirror)"
    )

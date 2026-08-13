# 공개 ticker Celery 태스크의 lease·빈 심볼·reconcile 동작을 DB 없이 검증한다.
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


class _Engine:
    async def dispose(self) -> None:
        return None


def _session_factory() -> object:
    @asynccontextmanager
    async def _session():
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        yield session

    class _SessionFactory:
        def __call__(self):
            return _session()

    return _SessionFactory()


@pytest.mark.asyncio
async def test_public_ticker_duplicate_lease_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.tasks import websocket_task

    monkeypatch.setattr(
        "src.tasks._ws_lease.acquire_ws_lease", AsyncMock(return_value=None)
    )

    assert await websocket_task._run_public_ticker_async() == {"status": "duplicate"}


@pytest.mark.asyncio
async def test_public_ticker_no_symbols_exits_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.tasks import websocket_task

    monkeypatch.setattr(
        websocket_task,
        "create_worker_engine_and_sm",
        lambda: (_Engine(), _session_factory()),
    )
    monkeypatch.setattr(
        websocket_task, "_list_active_ticker_symbols", AsyncMock(return_value=set())
    )

    assert await websocket_task._public_ticker_stream_main() == {"status": "no_symbols"}


@pytest.mark.asyncio
async def test_reconcile_enqueues_public_ticker_for_active_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.tasks import websocket_task

    monkeypatch.setattr(
        websocket_task,
        "create_worker_engine_and_sm",
        lambda: (_Engine(), _session_factory()),
    )

    class _Repo:
        def __init__(self, _session: object) -> None:
            pass

        async def list_distinct_active_symbols(self) -> list[str]:
            return ["BTC/USDT"]

    monkeypatch.setattr(
        "src.trading.repositories.live_signal_session_repository.LiveSignalSessionRepository",
        _Repo,
    )
    monkeypatch.setattr(
        "src.tasks._ws_lease.is_lease_active", AsyncMock(return_value=False)
    )
    delay = MagicMock()
    monkeypatch.setattr(websocket_task.run_bybit_public_ticker_stream, "delay", delay)

    result = await websocket_task._reconcile_async()

    assert result["public_ticker"] == "enqueued"
    delay.assert_called_once_with()


@pytest.mark.asyncio
async def test_reconcile_skips_public_ticker_with_active_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.tasks import websocket_task

    monkeypatch.setattr(
        websocket_task,
        "create_worker_engine_and_sm",
        lambda: (_Engine(), _session_factory()),
    )

    class _Repo:
        def __init__(self, _session: object) -> None:
            pass

        async def list_distinct_active_symbols(self) -> list[str]:
            return ["BTC/USDT"]

    monkeypatch.setattr(
        "src.trading.repositories.live_signal_session_repository.LiveSignalSessionRepository",
        _Repo,
    )
    monkeypatch.setattr(
        "src.tasks._ws_lease.is_lease_active", AsyncMock(return_value=True)
    )
    delay = MagicMock()
    monkeypatch.setattr(websocket_task.run_bybit_public_ticker_stream, "delay", delay)

    result = await websocket_task._reconcile_async()

    assert result["public_ticker"] == "skipped_active"
    delay.assert_not_called()


def test_public_ticker_task_has_ws_stream_routing() -> None:
    from src.tasks.celery_app import celery_app
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    routes = celery_app.conf.task_routes or {}
    assert (
        routes.get("trading.run_bybit_public_ticker_stream", {}).get("queue")
        == "ws_stream"
    )
    assert run_bybit_public_ticker_stream.queue == "ws_stream"

"""Sprint 17 Phase B — websocket_task prefork-safe 회귀 방어.

Phase 0 라이브 검증 (2026-05-02): 6h 동안 reconcile_ws_streams 18/35 fail
(RuntimeError "Future attached to a different loop") — `from src.common.database
import async_session_factory` (uvicorn 전역 module) + Celery prefork asyncio.run()
새 loop binding mismatch.

Fix: per-call create_worker_engine_and_sm() + finally engine.dispose() (backtest.py:31 mirror).
- `_reconcile_async` (5분 beat): per-call engine + finally dispose
- `_stream_main` (long-running): engine 1개 hold + finally dispose (codex G.0 P1 #3)
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


def _fake_create_worker_engine_and_sm(
    *,
    accounts: list | None = None,
) -> tuple[
    Callable[[], tuple[_RecordingEngine, object]],
    _RecordingEngine,
]:
    """create_worker_engine_and_sm mock for websocket_task tests."""
    engine = _RecordingEngine()

    @asynccontextmanager
    async def _session_ctx():
        session_mock = MagicMock()
        # accounts 가 주어지면 select query 결과로 반환
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = accounts or []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session_mock.execute = AsyncMock(return_value=result_mock)
        yield session_mock

    class _SM:
        def __call__(self):
            return _session_ctx()

    def _factory():
        return engine, _SM()

    return _factory, engine


# -------------------------------------------------------------------------
# Phase B-1: _reconcile_async — 5분 beat task
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_async_calls_create_worker_engine_and_sm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B — _reconcile_async 가 create_worker_engine_and_sm() 호출."""
    import src.tasks.websocket_task as ws_mod

    factory, _engine = _fake_create_worker_engine_and_sm(accounts=[])
    call_count = {"n": 0}

    def _spy_factory():
        call_count["n"] += 1
        return factory()

    monkeypatch.setattr(ws_mod, "create_worker_engine_and_sm", _spy_factory)

    await ws_mod._reconcile_async()

    assert call_count["n"] == 1, "create_worker_engine_and_sm 가 task 1회 호출"


@pytest.mark.asyncio
async def test_reconcile_async_disposes_engine_on_finally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B — 정상 path 에서 engine.dispose() 호출."""
    import src.tasks.websocket_task as ws_mod

    factory, engine = _fake_create_worker_engine_and_sm(accounts=[])
    monkeypatch.setattr(ws_mod, "create_worker_engine_and_sm", factory)

    await ws_mod._reconcile_async()

    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_reconcile_async_disposes_engine_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B — query 예외 시에도 dispose 호출."""
    import src.tasks.websocket_task as ws_mod

    engine = _RecordingEngine()

    @asynccontextmanager
    async def _bad_session_ctx():
        session_mock = MagicMock()
        session_mock.execute = AsyncMock(side_effect=RuntimeError("boom"))
        yield session_mock

    class _SM:
        def __call__(self):
            return _bad_session_ctx()

    monkeypatch.setattr(
        ws_mod, "create_worker_engine_and_sm", lambda: (engine, _SM())
    )

    with pytest.raises(RuntimeError, match="boom"):
        await ws_mod._reconcile_async()

    assert engine.dispose_calls == 1


def test_module_no_async_session_factory_global_import() -> None:
    """Phase B — module top-level 에 async_session_factory 잔존 차단.

    회귀 방어: src.common.database 의 uvicorn-only async_session_factory 가
    websocket_task module 에 다시 import 되면 Phase 0 의 18/35 fail 재발.
    """
    import src.tasks.websocket_task as ws_mod

    # module attribute 자체는 함수 안 lazy import 라 module 에 노출 X
    # 단, helper 가 추가됐는지는 검증
    assert hasattr(ws_mod, "create_worker_engine_and_sm"), (
        "create_worker_engine_and_sm helper 가 ws_mod 에 존재해야 함 (backtest.py mirror)"
    )


# -------------------------------------------------------------------------
# Phase B-2: _stream_main — long-running stream + 4 BaseException dispose
# -------------------------------------------------------------------------


class _StubBybitPrivateStream:
    """BybitPrivateStream context manager stub. raise_on_enter 로 예외 시뮬."""

    def __init__(
        self, *args: object, raise_on_enter: BaseException | None = None, **kwargs: object
    ) -> None:
        self.reconnect_count = 0
        self._raise = raise_on_enter

    async def __aenter__(self) -> _StubBybitPrivateStream:
        if self._raise is not None:
            raise self._raise
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _make_stream_main_environment(
    monkeypatch: pytest.MonkeyPatch,
    *,
    raise_on_enter: BaseException | None = None,
):
    """_stream_main 의 minimal mock environment 구성.

    Returns: (engine, account_id) tuple. engine.dispose_calls 검증용.
    """
    from uuid import uuid4

    import src.tasks.websocket_task as ws_mod

    engine = _RecordingEngine()
    account_id = str(uuid4())

    # mock account
    account_mock = MagicMock()
    account_mock.exchange = MagicMock()
    account_mock.api_key_encrypted = b"\x00"
    account_mock.api_secret_encrypted = b"\x00"
    account_mock.passphrase_encrypted = None
    account_mock.mode = MagicMock()
    account_mock.mode.value = "demo"

    @asynccontextmanager
    async def _session_ctx():
        session_mock = MagicMock()
        session_mock.get = AsyncMock(return_value=account_mock)
        yield session_mock

    class _SM:
        def __call__(self):
            return _session_ctx()

    monkeypatch.setattr(
        ws_mod, "create_worker_engine_and_sm", lambda: (engine, _SM())
    )

    # ExchangeName 비교 우회 — bybit 통과시키기
    from src.trading.models import ExchangeName
    account_mock.exchange = ExchangeName.bybit

    # EncryptionService.decrypt mock
    monkeypatch.setattr(
        "src.trading.encryption.EncryptionService.decrypt",
        lambda self, ct: "fake",
    )

    # BybitPrivateStream stub
    def _stub_stream_class(*args: object, **kwargs: object):
        return _StubBybitPrivateStream(*args, raise_on_enter=raise_on_enter, **kwargs)

    monkeypatch.setattr(
        "src.trading.websocket.BybitPrivateStream", _stub_stream_class
    )

    return engine, account_id


@pytest.mark.asyncio
async def test_stream_main_disposes_engine_on_BybitAuthError(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B P1 #3 — BybitAuthError 시 engine.dispose() finally 호출."""
    import src.tasks.websocket_task as ws_mod
    from src.trading.websocket import BybitAuthError

    engine, account_id = _make_stream_main_environment(
        monkeypatch, raise_on_enter=BybitAuthError("auth")
    )

    # send_critical_alert no-op (alert path 가 외부 의존)
    async def _noop_alert(*a, **kw):
        return True

    monkeypatch.setattr(ws_mod, "send_critical_alert", _noop_alert)

    result = await ws_mod._stream_main(account_id)
    assert result["status"] == "auth_failed"
    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_stream_main_disposes_engine_on_generic_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B P1 #3 — 일반 Exception 시에도 engine.dispose() finally 호출."""
    import src.tasks.websocket_task as ws_mod

    engine, account_id = _make_stream_main_environment(
        monkeypatch, raise_on_enter=RuntimeError("network kaput")
    )

    with pytest.raises(RuntimeError, match="network kaput"):
        await ws_mod._stream_main(account_id)

    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_stream_main_disposes_engine_on_CancelledError(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B P1 #3 — asyncio.CancelledError 시에도 engine.dispose() finally 호출."""
    import asyncio

    import src.tasks.websocket_task as ws_mod

    engine, account_id = _make_stream_main_environment(
        monkeypatch, raise_on_enter=asyncio.CancelledError()
    )

    with pytest.raises(asyncio.CancelledError):
        await ws_mod._stream_main(account_id)

    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_stream_main_disposes_engine_on_KeyboardInterrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase B P1 #3 — KeyboardInterrupt (BaseException) 시에도 finally 호출.

    BaseException 류는 try/finally 가 통과 보장 — Python 공식. test 가 회귀 방어.
    """
    import src.tasks.websocket_task as ws_mod

    engine, account_id = _make_stream_main_environment(
        monkeypatch, raise_on_enter=KeyboardInterrupt()
    )

    with pytest.raises(KeyboardInterrupt):
        await ws_mod._stream_main(account_id)

    assert engine.dispose_calls == 1

"""WebSocket Celery task의 종료·lease 런타임 분기를 외부 I/O 없이 고정한다."""

from __future__ import annotations

import asyncio
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.parametrize(
    ("task_name", "coroutine_name", "expected"),
    [
        ("run_bybit_private_stream", "_run_async", {"status": "private"}),
        ("run_bybit_public_ticker_stream", "_run_public_ticker_async", {"status": "public"}),
    ],
)
def test_stream_task_wrappers_delegate_one_coroutine_to_persistent_worker_loop(
    monkeypatch: pytest.MonkeyPatch,
    task_name: str,
    coroutine_name: str,
    expected: dict[str, str],
) -> None:
    """sync Celery wrapper는 asyncio.run이 아니라 영속 worker loop에 단 한 번 위임한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    async_entry = AsyncMock()
    received: list[object] = []

    def run_in_worker_loop(coroutine: object) -> dict[str, str]:
        received.append(coroutine)
        coroutine.close()  # type: ignore[union-attr]
        return expected

    monkeypatch.setattr(websocket_module, coroutine_name, async_entry)
    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", run_in_worker_loop)

    if task_name == "run_bybit_private_stream":
        result = getattr(websocket_module, task_name).run("account-1")
        async_entry.assert_called_once_with("account-1")
    else:
        result = getattr(websocket_module, task_name).run()
        async_entry.assert_called_once_with()

    assert result is expected
    assert len(received) == 1
    assert asyncio.iscoroutine(received[0])


def test_signal_all_stop_events_ignores_one_failed_loop() -> None:
    """한 stream loop의 cross-thread signal 실패는 다른 종료 훅을 중단하지 않는다."""
    websocket_module = import_module("src.tasks.websocket_task")
    failed_loop = MagicMock()
    failed_loop.call_soon_threadsafe.side_effect = RuntimeError("loop closed")
    event = asyncio.Event()

    with websocket_module._STOP_EVENTS_LOCK:
        websocket_module._STOP_EVENTS["failed-account"] = (failed_loop, event)
    try:
        assert websocket_module.signal_all_stop_events() == 0
        assert event.is_set() is False
    finally:
        with websocket_module._STOP_EVENTS_LOCK:
            websocket_module._STOP_EVENTS.pop("failed-account", None)


@pytest.mark.asyncio
async def test_public_ticker_first_connect_timeout_records_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """공개 ticker의 최초 연결 timeout은 circuit breaker 입력으로 변환한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    circuit_breaker_module = import_module("src.tasks._ws_circuit_breaker")
    public_stream_module = import_module("src.trading.websocket.bybit_public_stream")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    record_network_failure = AsyncMock(return_value=True)

    class _FirstConnectTimeoutStream:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _FirstConnectTimeoutStream:
            raise TimeoutError("first connection timed out")

        async def __aexit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(websocket_module, "create_worker_engine_and_sm", lambda: (engine, object()))
    monkeypatch.setattr(
        websocket_module,
        "_list_active_ticker_symbols",
        AsyncMock(return_value={"BTCUSDT"}),
    )
    monkeypatch.setattr(circuit_breaker_module, "record_network_failure", record_network_failure)
    monkeypatch.setattr(public_stream_module, "BybitPublicTickerStream", _FirstConnectTimeoutStream)

    result = await websocket_module._public_ticker_stream_main()

    assert result == {"status": "first_connect_timeout", "circuit_opened": True}
    record_network_failure.assert_awaited_once_with(websocket_module._PUBLIC_TICKER_LEASE_ID)
    engine.dispose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_lease_heartbeat_marks_lost_when_extend_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """heartbeat extend 실패는 split-brain 방지를 위해 lost_event를 set하고 끝낸다."""
    lease_module = import_module("src.tasks._ws_lease")
    lock = MagicMock()
    lock.extend = AsyncMock(return_value=False)
    lost_event = asyncio.Event()
    lease = lease_module.WsLease(lock, "account-1", ttl_ms=3, lost_event=lost_event)

    monkeypatch.setattr(lease_module.asyncio, "sleep", AsyncMock())

    await lease._heartbeat_loop()

    lock.extend.assert_awaited_once_with(3)
    assert lost_event.is_set()

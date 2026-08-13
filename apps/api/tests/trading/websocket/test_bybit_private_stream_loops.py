# BybitPrivateStream 의 미커버 루프 분기(_receive_loop / _heartbeat / _maybe_reconcile / auth timeout) 보강
"""BybitPrivateStream 내부 루프 TDD (BL-308, W3).

기존 test_bybit_private_stream.py 는 auth success/fail, reconnect, aexit, fd-leak,
debounce-skip, sign 을 덮는다. baseline term-missing(75%)이 가리킨 잔여 = 수신/하트비트
루프 본문과 auth timeout. 이들은 money-path silent-fail 분기:
- _receive_loop: malformed JSON skip / non-order topic skip / handler None skip /
  handler 예외 swallow 후 다음 item 계속 처리 (fill 이벤트 드롭 경로, bybit:173-194).
- _heartbeat_loop: stop 까지 ping / ConnectionClosed graceful 종료 (bybit:160-169).
- _maybe_reconcile: reconciler.run 예외 swallow (bybit:157-158).
- _authenticate: recv timeout → BybitAuthError (bybit:128-129).
- _close_ws_safely: close 예외 swallow + FD None 보장 (bybit:204-205).
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import src.trading.websocket.bybit_private_stream as stream_mod
from src.trading.websocket.bybit_private_stream import BybitAuthError, BybitPrivateStream


def _make_stream(**kwargs) -> BybitPrivateStream:
    return BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=kwargs.pop("account_id", uuid4()),
        **kwargs,
    )


def _order_msg(order_link_id: str, status: str = "Filled") -> dict:
    return {
        "topic": "order",
        "data": [{"orderLinkId": order_link_id, "orderStatus": status}],
    }


async def test_receive_loop_skips_malformed_json(fake_ws):
    """malformed JSON → JSONDecodeError continue, 이후 valid item 정상 처리."""
    handler = AsyncMock()
    stream = _make_stream(handler=handler)
    stream._ws = fake_ws
    fake_ws._recv_queue.put_nowait("{not valid json")  # raw 비-JSON
    fake_ws.queue_recv(_order_msg("link-1"))
    fake_ws.queue_close()

    await asyncio.wait_for(stream._receive_loop(), timeout=2.0)

    handler.handle_order_event.assert_awaited_once()
    assert handler.handle_order_event.await_args[0][1]["orderLinkId"] == "link-1"


async def test_receive_loop_skips_non_order_topic(fake_ws):
    """topic != 'order' → skip, 이후 order 메시지는 처리.

    G2: '한 번 호출'만으로는 topic guard 가 반전돼 wallet 을 처리하고 order 를
    skip 해도 통과(wrong-seam) → 처리된 payload 가 *order* 임을 단언.
    """
    handler = AsyncMock()
    stream = _make_stream(handler=handler)
    stream._ws = fake_ws
    fake_ws.queue_recv({"topic": "wallet", "data": [{"orderLinkId": "wallet-evt"}]})
    fake_ws.queue_recv(_order_msg("link-2"))
    fake_ws.queue_close()

    await asyncio.wait_for(stream._receive_loop(), timeout=2.0)

    handler.handle_order_event.assert_awaited_once()
    assert handler.handle_order_event.await_args[0][1]["orderLinkId"] == "link-2"


async def test_receive_loop_handler_none_skips(fake_ws, caplog):
    """handler 미주입 → 'handler is None' guard 가 data 루프 진입 전 skip.

    G2 false-green 방어: guard 가 삭제되면 `None.handle_order_event` 가 broad
    except 에 잡혀 'ws_handler_failed' 로그만 남고 여전히 통과한다 → guard 가
    실제로 handler 호출 자체를 막았음을 'ws_handler_failed' 미발생으로 단언.
    """
    stream = _make_stream(handler=None)
    stream._ws = fake_ws
    fake_ws.queue_recv(_order_msg("link-3"))
    fake_ws.queue_close()

    with caplog.at_level(logging.WARNING, logger="src.trading.websocket.bybit_private_stream"):
        await asyncio.wait_for(stream._receive_loop(), timeout=2.0)

    assert "ws_handler_failed" not in caplog.text  # guard 가 handler 호출 자체를 차단


async def test_receive_loop_handler_exception_swallowed_continues(fake_ws):
    """handler 예외 → swallow + 다음 item 계속 처리 (fill silent-fail 분기).

    money-path: 한 이벤트 처리 실패가 후속 이벤트 처리를 막으면 안 된다.
    'does not raise' 만으로는 vacuous → 두 번째 item 이 실제로 처리됨을 단언.
    """
    handler = AsyncMock()
    handler.handle_order_event = AsyncMock(side_effect=[RuntimeError("boom"), None])
    stream = _make_stream(handler=handler)
    stream._ws = fake_ws
    fake_ws.queue_recv(_order_msg("link-fail"))
    fake_ws.queue_recv(_order_msg("link-ok"))
    fake_ws.queue_close()

    await asyncio.wait_for(stream._receive_loop(), timeout=2.0)

    assert handler.handle_order_event.await_count == 2  # 첫 예외 후에도 계속
    assert handler.handle_order_event.await_args_list[1][0][1]["orderLinkId"] == "link-ok"


async def test_receive_loop_stop_event_breaks(fake_ws):
    """stop_event set → 루프 즉시 return (bybit:176-177)."""
    handler = AsyncMock()
    stop = asyncio.Event()
    stop.set()
    stream = _make_stream(handler=handler, stop_event=stop)
    stream._ws = fake_ws
    fake_ws.queue_recv(_order_msg("link-x"))
    fake_ws.queue_close()

    await asyncio.wait_for(stream._receive_loop(), timeout=2.0)
    handler.handle_order_event.assert_not_awaited()


async def test_heartbeat_sends_ping_until_stop(fake_ws):
    """stop 전까지 주기적으로 ping 송신 (bybit:162-167)."""
    stream = _make_stream(heartbeat_interval=0.01)
    stream._ws = fake_ws
    task = asyncio.create_task(stream._heartbeat_loop())
    await asyncio.sleep(0.05)  # 여러 interval 경과 → 최소 1 ping
    stream._stop_event.set()
    await asyncio.wait_for(task, timeout=2.0)

    pings = [m for m in fake_ws.sent if m.get("op") == "ping"]
    assert len(pings) >= 1


async def test_heartbeat_connection_closed_exits(fake_ws):
    """send 가 ConnectionClosed → 루프 graceful 종료 (bybit:168-169)."""
    fake_ws._closed = True  # send 시 ConnectionClosed raise
    stream = _make_stream(heartbeat_interval=0.01)
    stream._ws = fake_ws
    # stop 미set 이라도 send 예외로 스스로 종료해야 함 (hang 금지)
    await asyncio.wait_for(stream._heartbeat_loop(), timeout=2.0)
    assert fake_ws.sent == []  # send 가 append 전에 raise


async def test_maybe_reconcile_exception_swallowed():
    """reconciler.run 예외 → swallow, 미전파 (bybit:157-158)."""
    reconciler = AsyncMock()
    reconciler.run = AsyncMock(side_effect=RuntimeError("reconcile boom"))
    stream = _make_stream(reconciler=reconciler)
    # 예외 없이 반환해야 함 (supervisor 미중단)
    await stream._maybe_reconcile()
    reconciler.run.assert_awaited_once()


async def test_authenticate_timeout_raises_auth_error(fake_ws, monkeypatch):
    """recv 가 timeout 안에 안 오면 BybitAuthError (bybit:128-129).

    실제 5s 대기 대신 _AUTH_TIMEOUT_S 를 0.05 로 monkeypatch + recv 빈 큐(hang).
    """
    monkeypatch.setattr(stream_mod, "_AUTH_TIMEOUT_S", 0.05)
    stream = _make_stream()
    stream._ws = fake_ws  # recv 큐 비어 있음 → 영원히 대기 → wait_for timeout
    with pytest.raises(BybitAuthError, match="timeout"):
        await stream._authenticate()


async def test_close_ws_safely_swallows_close_exception():
    """ws.close 예외 → swallow + _ws None 보장 (FD leak 방지, bybit:204-207)."""

    class _BadWs:
        async def close(self, code: int = 1000) -> None:
            raise RuntimeError("close failed")

    stream = _make_stream()
    stream._ws = _BadWs()
    await stream._close_ws_safely()  # 예외 없이
    assert stream._ws is None


async def test_wait_supervisor_done_noop_when_no_task():
    """supervisor task 없음 → no-op return (bybit:307-308)."""
    stream = _make_stream()
    stream._supervisor_task = None
    await stream._wait_supervisor_done()  # 예외 없이

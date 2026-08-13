"""Sprint 12 Phase C — BybitPrivateStream TDD.

7 시나리오 (M2 Slim):
1. authenticate_success — auth response success=True 받고 subscribe 진행
2. authenticate_failure_raises — success=False → BybitAuthError + reconnect 안 함
3. message_dispatched_via_orderLinkId — payload.orderLinkId 로 handler 호출
4. first_connect_triggers_reconcile — first connect 도 reconciler.run 호출 (G3 #11)
5. reconcile_debounce_skips_within_30s — 두 번째 reconnect 가 30s 내면 skip + metric
6. stop_event_breaks_aenter_loop — stop_event set 시 connect 루프 break
7. sign_function_matches_bybit_v5_spec — `GET/realtime{expires}` HMAC-SHA256
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.websocket.bybit_private_stream import (
    BybitAuthError,
    BybitPrivateStream,
)


def _success_auth() -> dict[str, object]:
    return {"op": "auth", "success": True, "ret_msg": "ok"}


def _failure_auth() -> dict[str, object]:
    return {
        "op": "auth",
        "success": False,
        "ret_msg": "Invalid signature. Check timestamp +/- 5s drift.",
    }


@pytest.mark.asyncio
async def test_authenticate_success_sends_signed_payload_and_subscribes(
    fake_ws, fake_connect
):
    fake_ws.queue_recv(_success_auth())
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="key123",
        api_secret="secret456",
        account_id=uuid4(),
        connect_func=fake_connect,
    )
    async with stream:
        # auth payload + subscribe payload 송신 확인
        assert len(fake_ws.sent) >= 2
        auth_msg = fake_ws.sent[0]
        sub_msg = fake_ws.sent[1]
    assert auth_msg["op"] == "auth"
    assert auth_msg["args"][0] == "key123"
    # signature is hex-encoded HMAC-SHA256, 64 chars
    assert len(auth_msg["args"][2]) == 64
    assert sub_msg == {"op": "subscribe", "args": ["order"]}
    assert stream.connected is False  # __aexit__ 가 False 로 reset


@pytest.mark.asyncio
async def test_authenticate_failure_raises_BybitAuthError(fake_ws, fake_connect):
    fake_ws.queue_recv(_failure_auth())
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="key",
        api_secret="secret",
        account_id=uuid4(),
        connect_func=fake_connect,
    )
    with pytest.raises(BybitAuthError, match="Invalid signature"):
        async with stream:
            pass
    # subscribe 송신 안 됨
    assert all(m.get("op") != "subscribe" for m in fake_ws.sent)


@pytest.mark.asyncio
async def test_first_connect_triggers_reconcile(fake_ws, fake_connect):
    """codex G3 #11 — first connect 도 reconciler.run 호출."""
    fake_ws.queue_recv(_success_auth())
    reconciler = AsyncMock()
    reconciler.run = AsyncMock(return_value=None)
    account_id = uuid4()
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=account_id,
        reconciler=reconciler,
        connect_func=fake_connect,
    )
    async with stream:
        pass
    reconciler.run.assert_called_once_with(account_id=account_id)


@pytest.mark.asyncio
async def test_reconcile_debounce_skips_within_30s(fake_connect):
    """codex G3 #4 — 30s 내 두 번째 호출은 skip."""
    from src.trading.websocket.bybit_private_stream import BybitPrivateStream

    reconciler = AsyncMock()
    reconciler.run = AsyncMock(return_value=None)
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        reconciler=reconciler,
        connect_func=fake_connect,
    )

    # 첫 번째 — debounce 0 → 호출
    await stream._maybe_reconcile()
    assert reconciler.run.await_count == 1

    # 두 번째 — 30s 내 → skip
    await stream._maybe_reconcile()
    assert reconciler.run.await_count == 1  # 증가 없음


@pytest.mark.asyncio
async def test_stop_event_set_before_connect_raises(fake_connect):
    """stop_event 가 이미 set 인 상태로 진입 → connect 루프 break."""
    stop = asyncio.Event()
    stop.set()
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        stop_event=stop,
        connect_func=fake_connect,
    )
    with pytest.raises(RuntimeError, match="stop_event"):
        async with stream:
            pass


@pytest.mark.asyncio
async def test_reconnect_after_connection_closed(fake_ws, monkeypatch):
    """G4 fix #1: supervisor 가 ConnectionClosed 후 자동 재연결.

    fake_ws_first 가 close 되면 connect_func 가 fake_ws_second 를 반환.
    """
    from src.trading.websocket.bybit_private_stream import BybitPrivateStream
    from tests.trading.websocket.conftest import FakeWebSocket

    fake_ws_2 = FakeWebSocket()
    fake_ws.queue_recv(_success_auth())
    fake_ws_2.queue_recv(_success_auth())

    call_count = 0

    async def connect_sequence(_endpoint):
        nonlocal call_count
        call_count += 1
        return fake_ws if call_count == 1 else fake_ws_2

    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=connect_sequence,
    )

    async with stream:
        # 첫 연결 후 force close
        fake_ws.queue_close()
        # supervisor 가 재연결 시도할 시간 — 기본 backoff 1.0s + 여유
        # backoff 후 두 번째 connect_func 호출 + auth 까지 wait
        for _ in range(40):
            if stream.reconnect_count >= 1 and call_count >= 2:
                break
            await asyncio.sleep(0.05)
    assert stream.reconnect_count >= 1, (
        f"reconnect_count={stream.reconnect_count} call_count={call_count}"
    )
    assert call_count >= 2, (
        f"reconnect_count={stream.reconnect_count} call_count={call_count}"
    )


@pytest.mark.asyncio
async def test_aexit_closes_websocket_cleanly(fake_ws, fake_connect):
    """G4 fix #5: __aexit__ 가 ws close 보장."""
    fake_ws.queue_recv(_success_auth())
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=fake_connect,
    )
    async with stream:
        pass
    # supervisor 종료 + ws close 호출됨
    assert stream._supervisor_task is not None
    assert stream._supervisor_task.done()
    assert fake_ws._closed is True


@pytest.mark.asyncio
async def test_auth_failure_closes_websocket_no_fd_leak(fake_ws, fake_connect):
    """G4 fix #5: auth 실패 시 ws close 보장 (FD leak 방지)."""
    fake_ws.queue_recv(_failure_auth())
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=fake_connect,
    )
    with pytest.raises(BybitAuthError):
        async with stream:
            pass
    # supervisor finally 가 ws close
    assert fake_ws._closed is True


@pytest.mark.asyncio
async def test_sign_matches_bybit_v5_spec():
    """`GET/realtime{expires}` HMAC-SHA256 hex 검증."""
    import hashlib
    import hmac

    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="my-secret",
        account_id=uuid4(),
    )
    expires = 1700000000000
    sig = stream._sign(expires)
    expected = hmac.new(
        b"my-secret",
        f"GET/realtime{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert sig == expected
    assert len(sig) == 64


@pytest.mark.asyncio
async def test_auth_expires_window_survives_round_trip_latency(fake_ws, fake_connect):
    """auth `expires` 는 왕복 지연을 견딜 만큼 앞서 있어야 한다.

    ★실측 회귀(2026-07-26). 이전 값 `+1s` 는 프레임이 Bybit 서버에 닿는 시점에
    이미 만료돼 `Params Error` 로 거부됐다. demo·mainnet 양쪽에서 동일하게
    재현되고 `+10s`/`+60s` 는 통과한다. 지연이 낮을 때만 붙는 시한폭탄이라
    스프린트마다 붙었다 떨어졌다 했다.

    하한 5s = Bybit 이 문서에 적은 시계 드리프트 허용(±5s)과 같은 크기. 그보다
    좁으면 드리프트만으로도 창이 사라진다.
    """
    fake_ws.queue_recv(_success_auth())
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="key123",
        api_secret="secret456",
        account_id=uuid4(),
        connect_func=fake_connect,
    )
    before_ms = int(time.time() * 1000)
    async with stream:
        auth_msg = fake_ws.sent[0]

    expires = auth_msg["args"][1]
    assert isinstance(expires, int), "Bybit 은 정수 ms 를 요구한다"
    lead_ms = expires - before_ms
    assert lead_ms >= 5_000, (
        f"expires 가 현재보다 {lead_ms}ms 앞설 뿐이다 — 왕복 지연에 먹힌다. "
        "실측상 +1s 는 Params Error 로 거부됐다."
    )

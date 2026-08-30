"""[BL-837] supervisor 가 예상 밖 예외로 죽을 때 그것이 **보이는가**.

★**결함의 모양** — `_supervisor_loop` 이 잡는 예외는 `BybitAuthError`(fatal) ·
`ConnectionClosed`/`OSError`(재시도) · `CancelledError`(종료) 셋뿐이다. 그 밖의 예외는
task 에 저장된 채 **아무도 안 읽는다**. `__aenter__` 는 첫 연결만 기다리고 돌아가고,
다음 관측 시점은 `__aexit__` 의 `_wait_supervisor_done()` 인데 **거기까지 못 간다** —
`websocket_task._stream_main` 이 `await stop_event.wait()` 에서 영원히 멈춰 있기 때문이다.
그 사이 `async with lease:` 가 `ws:lease:{account_id}` 를 계속 갱신하므로 **다른 워커가
넘겨받지도 못한다.** ⇒ private order stream 이 조용히 끊긴 채 failover 까지 막힌다.

★**이것이 가설이 아닌 이유** — 재연결 시 `self._connect_func(...)` 가 던지는 예외 중
`websockets.exceptions.InvalidStatus`(Bybit 가 403/429 를 주는 경우)는 `WebSocketException`
계열이라 **`OSError` 도 `ConnectionClosed` 도 아니다.** 잡히지 않는다.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

import src.trading.websocket.bybit_private_stream as stream_mod
from src.trading.websocket.bybit_private_stream import BybitPrivateStream


def _success_auth() -> dict[str, object]:
    return {"op": "auth", "success": True, "ret_msg": "ok"}


class _Boom(Exception):
    """`OSError`·`ConnectionClosed` 어느 쪽도 아닌 예외 — supervisor 가 안 잡는 종류."""


def _crash_counter_value() -> float:
    from src.common.metrics import qb_ws_supervisor_crash_total

    return qb_ws_supervisor_crash_total._value.get()  # type: ignore[attr-defined]


async def test_supervisor_crash_after_first_connect_sets_stop_event(fake_ws) -> None:
    """첫 연결 성공 후 재연결에서 죽으면 `stop_event` 가 set 돼 lease 가 풀린다.

    ★수리 전에는 이 단언이 **timeout** 이었다 — `stop_event` 를 아무도 안 set 했다.
    """
    attempts: list[int] = []

    async def connect_sequence(endpoint: str):
        attempts.append(1)
        if len(attempts) == 1:
            return fake_ws
        raise _Boom("bybit returned 403 on reconnect")

    fake_ws.queue_recv(_success_auth())
    stop_event = asyncio.Event()
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=connect_sequence,
        stop_event=stop_event,
    )
    before = _crash_counter_value()

    await stream.__aenter__()
    try:
        # 연결을 끊어 supervisor 를 재연결 경로로 보낸다 → 두 번째 connect 가 죽는다.
        fake_ws.queue_close()
        await asyncio.wait_for(stop_event.wait(), timeout=5.0)
    finally:
        await stream.__aexit__(None, None, None)

    assert isinstance(stream.supervisor_error, _Boom)
    assert _crash_counter_value() == before + 1
    assert len(attempts) == 2


async def test_supervisor_crash_during_first_connect_raises_from_aenter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 연결에서 죽으면 `__aenter__` 가 **원래 예외**를 그대로 올린다.

    ★수리 전에는 60s 를 기다린 뒤 `TimeoutError` 였다 — 진짜 원인(`_Boom`)은 어디에도
    안 나타났다. 그 다음 줄의 `RuntimeError("stop_event set before first connect")` 도
    거짓말이다: stop 을 누른 사람은 없고 supervisor 가 죽은 것이다.
    ★timeout 을 줄이는 이유는 **수리 전 red 를 60초 안 기다리려는 것**이고, 수리 후에는
    이 값에 닿기 전에 반환된다(그것 자체가 이 테스트가 재는 것 중 하나다).
    """
    monkeypatch.setattr(stream_mod, "_FIRST_CONNECT_TIMEOUT_S", 2.0)

    async def always_crash(endpoint: str):
        raise _Boom("bybit rejected the handshake")

    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=always_crash,
    )

    with pytest.raises(_Boom):
        await stream.__aenter__()

    assert isinstance(stream.supervisor_error, _Boom)


async def test_clean_shutdown_is_not_reported_as_a_crash(fake_ws, fake_connect) -> None:
    """음성 대조 — 정상 종료는 crash 가 아니다.

    이 대조가 없으면 done-callback 이 `CancelledError`(= `__aexit__` 가 건 취소)를
    「supervisor 가 죽었다」로 오보해도 위 두 테스트는 초록이다.
    """
    fake_ws.queue_recv(_success_auth())
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=fake_connect,
    )
    before = _crash_counter_value()

    async with stream:
        pass

    assert stream.supervisor_error is None
    assert _crash_counter_value() == before


async def test_external_stop_event_is_not_reported_as_a_crash(fake_ws, fake_connect) -> None:
    """음성 대조 — worker shutdown 이 건 `stop_event` 도 crash 가 아니다."""
    fake_ws.queue_recv(_success_auth())
    stop_event = asyncio.Event()
    stream = BybitPrivateStream(
        endpoint="wss://test",
        api_key="k",
        api_secret="s",
        account_id=uuid4(),
        connect_func=fake_connect,
        stop_event=stop_event,
    )
    before = _crash_counter_value()

    await stream.__aenter__()
    stop_event.set()
    fake_ws.queue_close()
    await stream.__aexit__(None, None, None)

    assert stream.supervisor_error is None
    assert _crash_counter_value() == before

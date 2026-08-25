"""parse-preview의 동기 파싱이 이벤트 루프를 멈추는 현재 동작을 고정한다."""

from __future__ import annotations

import asyncio
import time
from threading import Event, Timer
from typing import Any

import pytest

_PARSE_SOURCE = '//@version=5\nstrategy("event-loop-check")\n'
_HEARTBEAT_TARGET = 10
_BLOCKING_PARSE_SLEEP_S = 0.2
_OBSERVATION_WINDOW_S = _BLOCKING_PARSE_SLEEP_S / 2


def _start_observation_window(closed: Event) -> Timer:
    """파서 호출 중에만 하트비트가 양보할 수 있는 관측 창을 연다."""
    timer = Timer(_OBSERVATION_WINDOW_S, closed.set)
    timer.daemon = True
    timer.start()
    return timer


async def _count_heartbeat_ticks(parse_started: Event, window_closed: Event) -> int:
    await asyncio.to_thread(parse_started.wait)
    ticks = 0
    for _ in range(_HEARTBEAT_TARGET):
        if window_closed.is_set():
            break
        await asyncio.sleep(0)
        ticks += 1
    return ticks


async def _request_parse_preview_with_heartbeat(client, parse_started: Event, window_closed: Event):
    return await asyncio.gather(
        client.post("/api/v1/strategies/parse", json={"pine_source": _PARSE_SOURCE}),
        _count_heartbeat_ticks(parse_started, window_closed),
    )


@pytest.mark.asyncio
async def test_parse_preview_blocks_event_loop_when_parse_to_ast_blocks(
    client, mock_authed_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """현재는 동기 parse_to_ast가 하트비트 목표 전 루프를 점유한다."""
    parse_started = Event()
    window_closed = Event()
    timers: list[Timer] = []

    def blocking_parse_to_ast(_source: str) -> Any:
        timers.append(_start_observation_window(window_closed))
        parse_started.set()
        time.sleep(_BLOCKING_PARSE_SLEEP_S)
        return object()

    monkeypatch.setattr("src.strategy.service.parse_to_ast", blocking_parse_to_ast)

    try:
        response, ticks = await _request_parse_preview_with_heartbeat(
            client, parse_started, window_closed
        )
    finally:
        for timer in timers:
            timer.cancel()

    assert response.status_code == 200
    assert ticks < _HEARTBEAT_TARGET


@pytest.mark.asyncio
async def test_parse_preview_heartbeat_reaches_target_when_parse_to_ast_returns_immediately(
    client, mock_authed_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """같은 하네스가 즉시 반환하는 파서에서는 정상적으로 틱을 센다."""
    parse_started = Event()
    window_closed = Event()
    timers: list[Timer] = []

    def immediate_parse_to_ast(_source: str) -> Any:
        timers.append(_start_observation_window(window_closed))
        parse_started.set()
        return object()

    monkeypatch.setattr("src.strategy.service.parse_to_ast", immediate_parse_to_ast)

    try:
        response, ticks = await _request_parse_preview_with_heartbeat(
            client, parse_started, window_closed
        )
    finally:
        for timer in timers:
            timer.cancel()

    assert response.status_code == 200
    assert ticks == _HEARTBEAT_TARGET


@pytest.mark.asyncio
async def test_parse_preview_calls_service_parse_to_ast(
    client, mock_authed_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """엔드포인트 요청이 service 모듈의 parse_to_ast 이름에 실제로 도달한다."""
    calls = 0

    def recording_parse_to_ast(_source: str) -> Any:
        nonlocal calls
        calls += 1
        return object()

    monkeypatch.setattr("src.strategy.service.parse_to_ast", recording_parse_to_ast)

    response = await client.post("/api/v1/strategies/parse", json={"pine_source": _PARSE_SOURCE})

    assert response.status_code == 200
    assert calls >= 1

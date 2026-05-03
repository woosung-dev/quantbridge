"""Sprint 12 Phase C — Celery ws_stream queue routing + acks_late + duplicate guard.

운영 모델 (codex G3 #3) 검증:
1. task_acks_late=True
2. task_reject_on_worker_lost=True
3. worker_prefetch_multiplier=1
4. trading.run_bybit_private_stream → ws_stream queue routing
5. reconcile-ws-streams beat schedule 등록 (5분 주기)
6. duplicate enqueue → process-level guard 가 no-op return
"""

from __future__ import annotations

import pytest


def test_celery_acks_late_enabled():
    from src.tasks.celery_app import celery_app

    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_celery_routes_ws_stream_queue():
    from src.tasks.celery_app import celery_app

    routes = celery_app.conf.task_routes or {}
    assert routes.get("trading.run_bybit_private_stream", {}).get("queue") == "ws_stream"


def test_beat_schedule_includes_reconcile_ws_streams():
    from src.tasks.celery_app import celery_app

    sched = celery_app.conf.beat_schedule
    assert "reconcile-ws-streams" in sched
    entry = sched["reconcile-ws-streams"]
    assert entry["task"] == "trading.reconcile_ws_streams"
    assert entry["schedule"] == 300.0  # 5분


@pytest.mark.asyncio
async def test_duplicate_enqueue_returns_no_op():
    """Sprint 24 BL-011 마이그레이션 (codex G.2 P1 #2 fix) —
    process-level _PROCESS_ACTIVE_STREAMS 제거됨, Redis lease 가 None 반환 시 duplicate 처리.

    이전 (Sprint 12): _PROCESS_LOCK + _PROCESS_ACTIVE_STREAMS set 직접 추가.
    이후 (Sprint 24): acquire_ws_lease mock → None 반환 (contention 시뮬).
    """
    from unittest.mock import AsyncMock, patch

    from src.tasks import websocket_task

    account_id = "00000000-0000-0000-0000-000000000001"
    # acquire_ws_lease mock — None 반환 (다른 worker 가 이미 보유 시뮬)
    with (
        patch("src.tasks._ws_circuit_breaker.is_circuit_open", new=AsyncMock(return_value=False)),
        patch("src.tasks._ws_lease.acquire_ws_lease", new=AsyncMock(return_value=None)),
    ):
        result = await websocket_task._run_async(account_id)
    assert result == {"status": "duplicate", "account_id": account_id}


@pytest.mark.asyncio
async def test_signal_all_stop_events_signals_registered():
    """G4 fix #4 — _STOP_EVENTS 에 등록된 stream 이 worker_shutdown 시 set 됨."""
    import asyncio

    from src.tasks import websocket_task

    loop = asyncio.get_running_loop()
    evt1 = asyncio.Event()
    evt2 = asyncio.Event()
    with websocket_task._STOP_EVENTS_LOCK:
        websocket_task._STOP_EVENTS["acc-1"] = (loop, evt1)
        websocket_task._STOP_EVENTS["acc-2"] = (loop, evt2)
    try:
        count = websocket_task.signal_all_stop_events()
        # call_soon_threadsafe 는 다음 loop iteration 에 실행
        await asyncio.sleep(0.01)
        assert count == 2
        assert evt1.is_set() is True
        assert evt2.is_set() is True
    finally:
        with websocket_task._STOP_EVENTS_LOCK:
            websocket_task._STOP_EVENTS.pop("acc-1", None)
            websocket_task._STOP_EVENTS.pop("acc-2", None)


def test_signal_all_stop_events_empty_returns_zero():
    """등록된 stream 없으면 count=0."""
    from src.tasks import websocket_task

    with websocket_task._STOP_EVENTS_LOCK:
        snapshot_size = len(websocket_task._STOP_EVENTS)
    if snapshot_size == 0:
        assert websocket_task.signal_all_stop_events() == 0

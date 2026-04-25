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
    """codex G3 #6 — process-level guard 가 두 번째 호출 시 raise 대신 no-op."""
    from src.tasks import websocket_task

    account_id = "00000000-0000-0000-0000-000000000001"
    # 첫 번째 진입처럼 보이도록 set 에 추가
    with websocket_task._PROCESS_LOCK:
        websocket_task._PROCESS_ACTIVE_STREAMS.add(account_id)
    try:
        result = await websocket_task._run_async(account_id)
        assert result == {"status": "duplicate", "account_id": account_id}
    finally:
        with websocket_task._PROCESS_LOCK:
            websocket_task._PROCESS_ACTIVE_STREAMS.discard(account_id)

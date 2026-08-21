"""Celery worker·beat 종료 훅의 prefork 수명주기 계약을 고정한다."""

from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _celery_module():
    """tasks 패키지 재export를 피해 실제 celery_app 모듈을 적재한다."""
    return import_module("src.tasks.celery_app")


def test_child_shutdown_signals_stream_then_closes_loop_and_marks_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """prefork child 종료는 stream 중단 뒤 loop·multiprocess metric을 정리한다."""
    celery_module = _celery_module()
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    signal_all_stop_events = MagicMock(return_value=2)
    shutdown_worker_loop = MagicMock()
    mark_metrics_process_dead = MagicMock()

    monkeypatch.setattr(websocket_module, "signal_all_stop_events", signal_all_stop_events)
    monkeypatch.setattr(worker_loop_module, "shutdown_worker_loop", shutdown_worker_loop)
    monkeypatch.setattr(celery_module, "mark_metrics_process_dead", mark_metrics_process_dead)

    celery_module._shutdown_worker_state_on_child_exit()

    signal_all_stop_events.assert_called_once_with()
    shutdown_worker_loop.assert_called_once_with()
    mark_metrics_process_dead.assert_called_once_with()


def test_child_shutdown_continues_when_stream_signal_and_metrics_cleanup_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stream·metric 정리 실패는 worker loop 종료를 막지 않는다."""
    celery_module = _celery_module()
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    shutdown_worker_loop = MagicMock()

    monkeypatch.setattr(
        websocket_module,
        "signal_all_stop_events",
        MagicMock(side_effect=RuntimeError("stream signal failed")),
    )
    monkeypatch.setattr(worker_loop_module, "shutdown_worker_loop", shutdown_worker_loop)
    monkeypatch.setattr(
        celery_module,
        "mark_metrics_process_dead",
        MagicMock(side_effect=RuntimeError("metric cleanup failed")),
    )

    celery_module._shutdown_worker_state_on_child_exit()

    shutdown_worker_loop.assert_called_once_with()


def test_beat_init_registers_only_beat_metrics_exit_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """beat init은 child worker가 아닌 beat 프로세스에만 atexit 정리를 등록한다."""
    celery_module = _celery_module()
    register = MagicMock()

    monkeypatch.setattr(celery_module.atexit, "register", register)

    celery_module._register_beat_metrics_cleanup()

    register.assert_called_once_with(celery_module._mark_metrics_process_dead_on_beat_exit)


def test_worker_ccxt_provider_is_created_once_per_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """lazy CCXTProvider는 fork 뒤 첫 task에서만 만들고 같은 child에서 재사용한다."""
    celery_module = _celery_module()
    ccxt_module = import_module("src.market_data.providers.ccxt")
    provider = MagicMock()
    provider_factory = MagicMock(return_value=provider)

    monkeypatch.setattr(celery_module, "_ccxt_provider", None)
    monkeypatch.setattr(ccxt_module, "CCXTProvider", provider_factory)
    monkeypatch.setattr(
        celery_module,
        "settings",
        SimpleNamespace(default_exchange="bybit"),
    )

    first = celery_module.get_ccxt_provider_for_worker()
    second = celery_module.get_ccxt_provider_for_worker()

    assert first is provider
    assert second is provider
    provider_factory.assert_called_once_with(exchange_name="bybit")

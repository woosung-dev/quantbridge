"""Celery worker·beat 종료 훅의 prefork 수명주기 계약을 고정한다."""

from __future__ import annotations

import asyncio
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def _celery_module():
    """tasks 패키지 재export를 피해 실제 celery_app 모듈을 적재한다."""
    return import_module("src.tasks.celery_app")


def test_worker_logging_hook_delegates_to_shared_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """worker·beat logging hook은 공통 포매터 설정을 한 번 호출한다."""
    celery_module = _celery_module()
    configure_logging = MagicMock()

    monkeypatch.setattr(celery_module, "configure_logging", configure_logging)

    celery_module._configure_worker_logging()

    configure_logging.assert_called_once_with()


def test_child_init_creates_loop_resets_redis_pool_and_switches_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """prefork child 초기화는 loop·fork stale Redis pool·DNS resolver를 함께 준비한다."""
    import aiohttp.connector
    import aiohttp.resolver

    celery_module = _celery_module()
    redis_module = import_module("src.common.redis_client")
    worker_loop_module = import_module("src.tasks._worker_loop")
    init_worker_loop = MagicMock()
    reset_redis_lock_pool = MagicMock()

    monkeypatch.setattr(worker_loop_module, "init_worker_loop", init_worker_loop)
    monkeypatch.setattr(redis_module, "reset_redis_lock_pool", reset_redis_lock_pool)

    celery_module._init_worker_state_after_fork()

    init_worker_loop.assert_called_once_with()
    reset_redis_lock_pool.assert_called_once_with()
    assert aiohttp.connector.DefaultResolver is aiohttp.resolver.ThreadedResolver


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


def test_beat_exit_cleanup_marks_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """beat atexit callback은 multiprocess metric shard를 종료 처리한다."""
    celery_module = _celery_module()
    mark_metrics_process_dead = MagicMock()

    monkeypatch.setattr(celery_module, "mark_metrics_process_dead", mark_metrics_process_dead)

    celery_module._mark_metrics_process_dead_on_beat_exit()

    mark_metrics_process_dead.assert_called_once_with()


def test_worker_ready_reclaims_each_domain_after_task_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """master ready hook은 등록 검증 뒤 세 stale-reclaim coroutine을 모두 실행한다."""
    celery_module = _celery_module()
    backtest_module = import_module("src.tasks.backtest")
    optimizer_module = import_module("src.tasks.optimizer_tasks")
    stress_test_module = import_module("src.tasks.stress_test_tasks")
    reclaim_backtests = AsyncMock(return_value=1)
    reclaim_optimizations = AsyncMock(return_value=0)
    reclaim_stress_tests = AsyncMock(return_value=2)

    monkeypatch.setitem(celery_module.celery_app.tasks, "trading.refresh_closed_pnl", object())
    monkeypatch.setitem(celery_module.celery_app.tasks, "trading.sweep_closed_pnl", object())
    monkeypatch.setattr(backtest_module, "reclaim_stale_running", reclaim_backtests)
    monkeypatch.setattr(optimizer_module, "reclaim_stale_running", reclaim_optimizations)
    monkeypatch.setattr(stress_test_module, "reclaim_stale_running", reclaim_stress_tests)

    celery_module._on_worker_ready()

    reclaim_backtests.assert_awaited_once_with()
    reclaim_optimizations.assert_awaited_once_with()
    reclaim_stress_tests.assert_awaited_once_with()


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


def test_master_shutdown_closes_provider_then_loop_and_marks_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """유휴 master 종료는 stream 신호 뒤 provider·loop·metric을 순서대로 정리한다."""
    celery_module = _celery_module()
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    provider = MagicMock()
    provider.close = AsyncMock()
    signal_all_stop_events = MagicMock(return_value=1)
    shutdown_worker_loop = MagicMock()
    mark_metrics_process_dead = MagicMock()
    received: list[object] = []

    def run_in_worker_loop(coroutine: object) -> None:
        received.append(coroutine)
        asyncio.run(coroutine)  # type: ignore[arg-type]

    inactive_loop = MagicMock()
    inactive_loop.is_running.return_value = False
    monkeypatch.setattr(websocket_module, "signal_all_stop_events", signal_all_stop_events)
    monkeypatch.setattr(worker_loop_module, "_WORKER_LOOP", inactive_loop)
    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", run_in_worker_loop)
    monkeypatch.setattr(worker_loop_module, "shutdown_worker_loop", shutdown_worker_loop)
    monkeypatch.setattr(celery_module, "mark_metrics_process_dead", mark_metrics_process_dead)
    monkeypatch.setattr(celery_module, "_ccxt_provider", provider)

    celery_module._on_worker_shutdown()

    signal_all_stop_events.assert_called_once_with()
    provider.close.assert_awaited_once_with()
    assert len(received) == 1
    assert celery_module._ccxt_provider is None
    shutdown_worker_loop.assert_called_once_with()
    mark_metrics_process_dead.assert_called_once_with()


def test_master_shutdown_skips_cleanup_while_stream_loop_is_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """실행 중 stream loop에서는 OS 종료에 맡기고 provider·loop close를 건너뛴다."""
    celery_module = _celery_module()
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    provider = MagicMock()
    provider.close = AsyncMock()
    shutdown_worker_loop = MagicMock()
    mark_metrics_process_dead = MagicMock()
    running_loop = MagicMock()
    running_loop.is_running.return_value = True

    monkeypatch.setattr(websocket_module, "signal_all_stop_events", MagicMock(return_value=1))
    monkeypatch.setattr(worker_loop_module, "_WORKER_LOOP", running_loop)
    monkeypatch.setattr(worker_loop_module, "shutdown_worker_loop", shutdown_worker_loop)
    monkeypatch.setattr(celery_module, "mark_metrics_process_dead", mark_metrics_process_dead)
    monkeypatch.setattr(celery_module, "_ccxt_provider", provider)

    celery_module._on_worker_shutdown()

    provider.close.assert_not_called()
    shutdown_worker_loop.assert_not_called()
    mark_metrics_process_dead.assert_called_once_with()


def test_child_shutdown_marks_metrics_when_worker_loop_shutdown_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """child loop 종료 예외는 전파해도 metrics 정리는 finally에서 반드시 실행한다."""
    celery_module = _celery_module()
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    mark_metrics_process_dead = MagicMock()

    monkeypatch.setattr(websocket_module, "signal_all_stop_events", MagicMock(return_value=0))
    monkeypatch.setattr(
        worker_loop_module,
        "shutdown_worker_loop",
        MagicMock(side_effect=RuntimeError("worker loop shutdown failed")),
    )
    monkeypatch.setattr(celery_module, "mark_metrics_process_dead", mark_metrics_process_dead)

    with pytest.raises(RuntimeError, match="worker loop shutdown failed"):
        celery_module._shutdown_worker_state_on_child_exit()

    mark_metrics_process_dead.assert_called_once_with()


def test_beat_exit_logs_metric_cleanup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """beat atexit metric 실패는 logger에 남기고 process 종료를 막지 않는다."""
    celery_module = _celery_module()
    logger = MagicMock()

    monkeypatch.setattr(
        celery_module,
        "mark_metrics_process_dead",
        MagicMock(side_effect=RuntimeError("metric cleanup failed")),
    )
    monkeypatch.setattr(celery_module, "logger", logger)

    celery_module._mark_metrics_process_dead_on_beat_exit()

    logger.exception.assert_called_once_with("metrics_process_dead_mark_failed_on_beat_exit")


def test_worker_ready_rejects_missing_closed_pnl_tasks_before_reclaim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """필수 closed-PnL task 미등록은 error log 뒤 즉시 실패해 stale reclaim을 막는다."""
    celery_module = _celery_module()
    logger = MagicMock()

    monkeypatch.setitem(celery_module.celery_app.tasks, "trading.sweep_closed_pnl", object())
    monkeypatch.delitem(celery_module.celery_app.tasks, "trading.refresh_closed_pnl", raising=False)
    monkeypatch.setattr(celery_module, "logger", logger)

    with pytest.raises(
        RuntimeError, match=r"missing closed PnL tasks: \['trading.refresh_closed_pnl'\]"
    ):
        celery_module._on_worker_ready()

    logger.error.assert_called_once_with(
        "closed_pnl_tasks_missing", extra={"tasks": ["trading.refresh_closed_pnl"]}
    )


def test_worker_ready_logs_one_reclaim_failure_and_runs_remaining_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """한 도메인 reclaim 실패는 기록하지만 나머지 두 도메인 reclaim은 계속 실행한다."""
    celery_module = _celery_module()
    backtest_module = import_module("src.tasks.backtest")
    optimizer_module = import_module("src.tasks.optimizer_tasks")
    stress_test_module = import_module("src.tasks.stress_test_tasks")
    logger = MagicMock()
    reclaim_backtests = AsyncMock(side_effect=RuntimeError("backtest reclaim failed"))
    reclaim_optimizations = AsyncMock(return_value=0)
    reclaim_stress_tests = AsyncMock(return_value=1)

    monkeypatch.setitem(celery_module.celery_app.tasks, "trading.refresh_closed_pnl", object())
    monkeypatch.setitem(celery_module.celery_app.tasks, "trading.sweep_closed_pnl", object())
    monkeypatch.setattr(backtest_module, "reclaim_stale_running", reclaim_backtests)
    monkeypatch.setattr(optimizer_module, "reclaim_stale_running", reclaim_optimizations)
    monkeypatch.setattr(stress_test_module, "reclaim_stale_running", reclaim_stress_tests)
    monkeypatch.setattr(celery_module, "logger", logger)

    celery_module._on_worker_ready()

    reclaim_backtests.assert_awaited_once_with()
    reclaim_optimizations.assert_awaited_once_with()
    reclaim_stress_tests.assert_awaited_once_with()
    logger.exception.assert_called_once_with(
        "stale_reclaim_failed_on_startup domain=%s", "backtest"
    )
    logger.info.assert_called_once_with(
        "stale_reclaim_on_startup", extra={"domain": "stress_test", "reclaimed_count": 1}
    )


def test_master_shutdown_continues_after_provider_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """provider close 실패는 기록·singleton 해제 후 worker loop와 metrics 정리를 계속한다."""
    celery_module = _celery_module()
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    provider = MagicMock()
    provider.close = AsyncMock()
    logger = MagicMock()
    shutdown_worker_loop = MagicMock()
    mark_metrics_process_dead = MagicMock()
    inactive_loop = MagicMock()
    inactive_loop.is_running.return_value = False

    def fail_after_closing(coroutine: object) -> None:
        coroutine.close()  # type: ignore[union-attr]
        raise RuntimeError("provider close failed")

    monkeypatch.setattr(websocket_module, "signal_all_stop_events", MagicMock(return_value=0))
    monkeypatch.setattr(worker_loop_module, "_WORKER_LOOP", inactive_loop)
    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", fail_after_closing)
    monkeypatch.setattr(worker_loop_module, "shutdown_worker_loop", shutdown_worker_loop)
    monkeypatch.setattr(celery_module, "mark_metrics_process_dead", mark_metrics_process_dead)
    monkeypatch.setattr(celery_module, "logger", logger)
    monkeypatch.setattr(celery_module, "_ccxt_provider", provider)

    celery_module._on_worker_shutdown()

    provider.close.assert_called_once_with()
    assert celery_module._ccxt_provider is None
    logger.exception.assert_called_once_with("ccxt_close_failed_on_shutdown")
    shutdown_worker_loop.assert_called_once_with()
    mark_metrics_process_dead.assert_called_once_with()

"""BL-506 Prometheus 멀티프로세스 단위 테스트(DB 의존 없음)."""

from __future__ import annotations

import ast
import asyncio
import os
import subprocess
import sys
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from prometheus_client import CollectorRegistry, Gauge, generate_latest, values
from prometheus_client.multiprocess import MultiProcessCollector, mark_process_dead

from src.common import metrics as metrics_module
from src.common import metrics_multiproc
from src.common.metrics_multiproc import (
    _count_safely,
    _process_identifier,
    build_metrics_registry,
    configure_multiprocess,
    mark_metrics_process_dead,
    record_metric_safely,
    render_metrics,
    reset_metrics_registry,
)

_BACKEND_ROOT = Path(__file__).parents[2]
_METRICS_SOURCE = _BACKEND_ROOT / "src/common/metrics.py"


@pytest.fixture(autouse=True)
def _restore_metrics_globals() -> Iterator[None]:
    """테스트 사이 Prometheus 프로세스 전역 상태를 격리한다."""
    original_value_class = values.ValueClass
    original_identifier_prefix = metrics_multiproc._PROCESS_IDENTIFIER_PREFIX
    reset_metrics_registry()
    yield
    values.ValueClass = original_value_class
    metrics_multiproc._PROCESS_IDENTIFIER_PREFIX = original_identifier_prefix
    reset_metrics_registry()


def _use_identifier(identifier: str) -> None:
    values.ValueClass = values.MultiProcessValue(process_identifier=lambda: identifier)


def _collect(path: Path) -> str:
    registry = CollectorRegistry()
    MultiProcessCollector(registry, path=str(path))
    return generate_latest(registry).decode()


def test_process_identifier_sanitizes_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T1: underscore role은 mmap 파일명 parser를 깨뜨리지 않는다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "ws_stream")
    monkeypatch.delenv("HOSTNAME", raising=False)
    configure_multiprocess()
    identifier = _process_identifier()

    assert identifier == f"wsstream-{os.getpid()}"
    assert "_" not in identifier

    gauge = Gauge(
        "qb_test_identifier_format",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="all",
    )
    gauge.set(1)
    assert f'pid="{identifier}"' in _collect(tmp_path)


def test_gauge_multiprocess_modes_are_explicit() -> None:
    """T2: 5개 gauge가 지정된 집계 시맨틱을 사용한다."""
    expected = {
        "qb_active_orders": "sum",
        "qb_redis_lock_pool_healthy": "mostrecent",
        "qb_ws_orphan_buffer_size": "livesum",
        "qb_pending_alerts": "livesum",
        "qb_live_signal_outbox_pending_gauge": "mostrecent",
    }
    assert {name: getattr(metrics_module, name)._multiprocess_mode for name in expected} == expected

    tree = ast.parse(_METRICS_SOURCE.read_text())
    gauges = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Gauge"
    ]
    assert gauges
    assert all(
        any(
            keyword.arg == "multiprocess_mode"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value != "all"
            for keyword in gauge.keywords
        )
        for gauge in gauges
    )


def test_sum_gauge_round_trips_across_writer_identifiers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T3: 별도 writer 파일의 delta gauge는 2.0으로 합산된다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    _use_identifier("worker-1")
    worker_gauge = Gauge(
        "qb_test_sum_round_trip",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="sum",
    )
    worker_gauge.inc(3)

    _use_identifier("api-2")
    api_gauge = Gauge(
        "qb_test_sum_round_trip",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="sum",
    )
    api_gauge.dec()

    assert "qb_test_sum_round_trip 2.0" in _collect(tmp_path)


def test_role_prefixes_keep_writer_series_distinct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T4: 충돌 식별자는 series를 합치고 role 접두어는 이를 막는다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.delenv("HOSTNAME", raising=False)
    _use_identifier("same-1")
    first = Gauge(
        "qb_test_identifier_collision",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="all",
    )
    first.set(3)
    _use_identifier("same-1")
    second = Gauge(
        "qb_test_identifier_collision",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="all",
    )
    second.set(7)
    assert _collect(tmp_path).count("qb_test_identifier_collision{") == 1

    for role, value in (("worker", 3), ("api", 7)):
        monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
        monkeypatch.setenv("QB_METRICS_ROLE", role)
        configure_multiprocess()
        gauge = Gauge(
            "qb_test_role_prefix",
            "test",
            registry=CollectorRegistry(),
            multiprocess_mode="all",
        )
        gauge.set(value)

    rendered = _collect(tmp_path)
    assert f'pid="worker-{os.getpid()}"' in rendered
    assert f'pid="api-{os.getpid()}"' in rendered


def test_mark_process_dead_keeps_sum_and_removes_livesum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T5: sum은 delta를 보존하고 live gauge는 writer와 함께 사라진다."""
    assert metrics_module.qb_active_orders._multiprocess_mode == "sum"
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    _use_identifier("worker-7")
    sum_gauge = Gauge(
        "qb_test_sum_survives",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="sum",
    )
    sum_gauge.set(4)
    live_gauge = Gauge(
        "qb_test_livesum_removed",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="livesum",
    )
    live_gauge.set(5)

    mark_process_dead("worker-7", path=str(tmp_path))
    rendered = _collect(tmp_path)
    assert "qb_test_sum_survives 4.0" in rendered
    assert "qb_test_livesum_removed" not in rendered


def test_mark_metrics_process_dead_removes_only_live_gauges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T6: 정리는 role 접두어가 붙은 live gauge 파일만 대상으로 한다."""
    for name in (
        "gauge_livesum_worker-9.db",
        "gauge_sum_worker-9.db",
        "counter_worker-9.db",
    ):
        (tmp_path / name).touch()

    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "worker")
    monkeypatch.delenv("HOSTNAME", raising=False)
    monkeypatch.setattr(metrics_multiproc.os, "getpid", lambda: 9)
    configure_multiprocess()
    mark_metrics_process_dead()

    assert not (tmp_path / "gauge_livesum_worker-9.db").exists()
    assert (tmp_path / "gauge_sum_worker-9.db").exists()
    assert (tmp_path / "counter_worker-9.db").exists()


def test_build_metrics_registry_has_single_process_fallback_and_default_collectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T7: 공유 registry는 python과 GC collector 출력을 보존한다."""
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    assert build_metrics_registry() is None

    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    reset_metrics_registry()
    registry = build_metrics_registry()
    assert registry is not None
    rendered = generate_latest(registry)
    assert b"python_info" in rendered
    assert b"python_gc_objects_collected" in rendered


def test_render_metrics_collects_another_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T8: 렌더링은 다른 프로세스 식별자가 쓴 값을 읽는다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    _use_identifier("worker-8")
    gauge = Gauge(
        "qb_test_render_remote_value",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="sum",
    )
    gauge.set(11)

    reset_metrics_registry()
    assert b"qb_test_render_remote_value 11.0" in render_metrics()


def test_render_metrics_falls_back_from_zero_byte_mmap_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U1: 손상된 mmap 파일 하나가 /metrics 렌더를 실패시키지 않는다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    (tmp_path / "gauge_livesum_worker-1.db").touch()

    assert isinstance(render_metrics(), bytes)


def test_record_metric_safely_swallows_failure_counter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """관측 실패 계수 자체가 기록 불가여도 호출자를 막지 않는다."""
    mutation = Mock(side_effect=OSError("metrics mmap is read-only"))
    monkeypatch.setattr(
        metrics_module.qb_metrics_mutation_failed_total,
        "inc",
        Mock(side_effect=OSError("counter mmap is read-only")),
    )

    record_metric_safely(mutation)

    mutation.assert_called_once_with()


# ── BL-580 (2026-08-03 metric-guard-residual-close) — 가드 자체의 폭 ────────
#
# ★**주입 테스트만으로는 반쪽 수리를 못 잡는다** (codex G1 MAJOR).
# 25곳의 사이트 테스트는 `.labels` 를 폭파시켜 잰다. 그런데 `.labels()` 만 try 로 감싸고
# `.inc()` 를 밖에 두는 수리도 그 주입에서는 green 이 된다 — multiprocess 모드에서
# `.inc()` 는 **별도의 mmap write** 를 하므로 거기서도 던질 수 있다.
# ⇒ 가드가 **둘 다** 삼키는지를 여기서 따로 못 박는다.


def test_count_safely_swallows_labels_failure() -> None:
    """새 라벨 조합이 mmap 을 늘리다 실패해도 호출자를 막지 않는다 (BL-536 R2)."""
    counter = Mock()
    counter.labels = Mock(side_effect=OSError("mmap allocation failed"))

    _count_safely(counter, outcome="x")

    counter.labels.assert_called_once_with(outcome="x")


def test_count_safely_swallows_child_inc_failure() -> None:
    """라벨 조합은 만들어졌는데 증가 write 가 실패하는 경우도 삼켜야 한다."""
    child = Mock()
    child.inc = Mock(side_effect=OSError("mmap write failed"))
    counter = Mock()
    counter.labels = Mock(return_value=child)

    _count_safely(counter, outcome="x")

    counter.labels.assert_called_once_with(outcome="x")
    child.inc.assert_called_once_with()


def test_render_metrics_counts_zero_byte_mmap_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U2: multiprocess 렌더 폴백은 운영 지표로 남긴다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    (tmp_path / "gauge_livesum_worker-1.db").touch()
    before = metrics_module.qb_metrics_render_fallback_total._value.get()

    render_metrics()

    assert metrics_module.qb_metrics_render_fallback_total._value.get() == before + 1


def test_render_metrics_quarantines_corrupt_file_and_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V3: 손상 파일은 보존 격리하고 다음 scrape은 multiprocess로 복구한다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    corrupt = tmp_path / "gauge_livesum_worker-1.db"
    corrupt.touch()
    before = metrics_module.qb_metrics_render_fallback_total._value.get()

    assert isinstance(render_metrics(), bytes)
    assert not corrupt.exists()
    assert list(tmp_path.glob("gauge_livesum_worker-1.db.corrupt-*"))
    assert metrics_module.qb_metrics_render_fallback_total._value.get() == before + 1

    assert isinstance(render_metrics(), bytes)
    assert metrics_module.qb_metrics_render_fallback_total._value.get() == before + 1


def test_render_metrics_keeps_200_when_corrupt_file_quarantine_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V4: 격리 권한 오류는 /metrics fallback 응답을 막지 않는다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    corrupt = tmp_path / "gauge_livesum_worker-1.db"
    corrupt.touch()
    monkeypatch.setattr(
        metrics_multiproc.Path,
        "rename",
        lambda self, target: (_ for _ in ()).throw(PermissionError("read-only")),
    )

    assert isinstance(render_metrics(), bytes)
    assert corrupt.exists()


def test_build_metrics_registry_recreates_deleted_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U3: mount 디렉토리가 사후 삭제돼도 다음 scrape에서 복구한다."""
    metrics_path = tmp_path / "metrics"
    metrics_path.mkdir()
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(metrics_path))
    build_metrics_registry()
    metrics_path.rmdir()

    assert build_metrics_registry() is not None
    assert metrics_path.is_dir()
    assert isinstance(render_metrics(), bytes)


def test_metrics_import_configures_value_class_before_gauges(tmp_path: Path) -> None:
    """T9: 새 interpreter는 role 접두어가 있는 active-order 파일을 만든다."""
    environment = os.environ | {
        "PROMETHEUS_MULTIPROC_DIR": str(tmp_path),
        "QB_METRICS_ROLE": "ws_stream",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            ("from src.common.metrics import qb_active_orders; qb_active_orders.inc()"),
        ],
        cwd=_BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    names = {path.name for path in tmp_path.glob("*.db")}
    assert any(name.startswith("gauge_sum_wsstream-") for name in names)


def test_mostrecent_gauges_are_set_only() -> None:
    """T13: mostrecent gauge에는 inc/dec를 호출하지 않는다."""
    source_root = _BACKEND_ROOT / "src"
    for metric_name in (
        "qb_redis_lock_pool_healthy",
        "qb_live_signal_outbox_pending_gauge",
    ):
        calls = [
            method
            for path in source_root.rglob("*.py")
            for method in ("set", "inc", "dec")
            if f"{metric_name}.{method}(" in path.read_text()
        ]
        assert calls and set(calls) == {"set"}


def test_configure_multiprocess_creates_missing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T14: 비었거나 없는 mount는 metric 생성 전에 다시 만든다."""
    metrics_path = tmp_path / "missing"
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(metrics_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "api")
    configure_multiprocess()
    assert metrics_path.is_dir()

    gauge = Gauge(
        "qb_test_created_directory",
        "test",
        registry=CollectorRegistry(),
        multiprocess_mode="sum",
    )
    gauge.set(1)
    reset_metrics_registry()
    assert b"qb_test_created_directory 1.0" in render_metrics()


def test_process_identifier_includes_sanitized_hostname(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U6: scale된 컨테이너 writer는 hostname으로 서로 구분된다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "ws_stream")
    monkeypatch.setenv("HOSTNAME", "worker_01.a")
    configure_multiprocess()

    identifier = _process_identifier()

    assert identifier == f"wsstream-worker01a-{os.getpid()}"
    assert "_" not in identifier


def test_process_identifier_caches_environment_after_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U7: mmap write hot path는 환경 변수를 다시 읽지 않는다."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "worker")
    monkeypatch.setenv("HOSTNAME", "first")
    configure_multiprocess()
    identifier = _process_identifier()
    monkeypatch.setenv("QB_METRICS_ROLE", "changed")
    monkeypatch.setenv("HOSTNAME", "second")

    assert _process_identifier() == identifier


def test_worker_shutdown_marks_role_identifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T12: Celery child 종료는 role 접두어 문자열을 정리에 전달한다."""
    from src.tasks import _worker_loop, websocket_task

    celery_app_module = import_module("src.tasks.celery_app")

    calls: list[object] = []
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "worker")
    monkeypatch.delenv("HOSTNAME", raising=False)
    configure_multiprocess()
    monkeypatch.setattr(metrics_multiproc, "mark_process_dead", calls.append)
    monkeypatch.setattr(websocket_task, "signal_all_stop_events", lambda: 0)
    monkeypatch.setattr(_worker_loop, "shutdown_worker_loop", lambda: None)

    celery_app_module._shutdown_worker_state_on_child_exit()

    assert calls == [f"worker-{os.getpid()}"]


def test_worker_child_marks_metrics_dead_when_loop_shutdown_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U4: child loop cleanup 실패도 mmap live gauge 정리를 막지 않는다."""
    from src.tasks import _worker_loop, websocket_task

    celery_app_module = import_module("src.tasks.celery_app")
    calls: list[bool] = []

    monkeypatch.setattr(websocket_task, "signal_all_stop_events", lambda: 0)
    monkeypatch.setattr(
        _worker_loop,
        "shutdown_worker_loop",
        lambda: (_ for _ in ()).throw(RuntimeError("loop shutdown failed")),
    )
    monkeypatch.setattr(celery_app_module, "mark_metrics_process_dead", lambda: calls.append(True))

    with pytest.raises(RuntimeError, match="loop shutdown failed"):
        celery_app_module._shutdown_worker_state_on_child_exit()

    assert calls == [True]


def test_worker_master_marks_metrics_dead_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """U5: Celery master 종료도 자신의 live gauge 파일을 정리한다."""
    from src.tasks import _worker_loop, websocket_task

    celery_app_module = import_module("src.tasks.celery_app")
    calls: list[bool] = []
    monkeypatch.setattr(websocket_task, "signal_all_stop_events", lambda: 0)
    monkeypatch.setattr(_worker_loop, "shutdown_worker_loop", lambda: None)
    monkeypatch.setattr(celery_app_module, "_ccxt_provider", None)
    monkeypatch.setattr(celery_app_module, "mark_metrics_process_dead", lambda: calls.append(True))

    celery_app_module._on_worker_shutdown()

    assert calls == [True]


@pytest.mark.asyncio
async def test_lifespan_shutdown_marks_role_identifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T15: API 종료는 DB client 없이 자신의 live gauge 파일을 정리한다."""
    from src import main
    from src.common import redis_client
    from src.realtime import manager as realtime_manager

    class _Manager:
        async def listen(self) -> None:
            await asyncio.Future()

        async def close(self) -> None:
            return None

    calls: list[object] = []
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("QB_METRICS_ROLE", "api")
    monkeypatch.delenv("HOSTNAME", raising=False)
    configure_multiprocess()
    monkeypatch.setattr(main.settings, "ohlcv_provider", "fixture")
    monkeypatch.setattr(redis_client, "healthcheck_redis_lock", AsyncMock())
    monkeypatch.setattr(realtime_manager, "ConnectionManager", _Manager)
    monkeypatch.setattr(metrics_multiproc, "mark_process_dead", calls.append)

    async with main.lifespan(FastAPI()):
        pass

    assert calls == [f"api-{os.getpid()}"]

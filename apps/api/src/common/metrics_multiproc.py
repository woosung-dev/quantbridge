"""Prometheus 멀티프로세스 수집 도우미."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from itertools import count
from pathlib import Path
from typing import Any

from prometheus_client import CollectorRegistry, generate_latest, values
from prometheus_client.gc_collector import GCCollector
from prometheus_client.mmap_dict import MmapedDict
from prometheus_client.multiprocess import MultiProcessCollector, mark_process_dead
from prometheus_client.platform_collector import PlatformCollector
from prometheus_client.process_collector import ProcessCollector

logger = logging.getLogger(__name__)

_METRICS_REGISTRY: CollectorRegistry | None = None
_PROCESS_IDENTIFIER_PREFIX = "app"


def record_metric_safely(fn: Callable[..., object], *args: object) -> None:
    """Metric mutation failures never affect the caller's business operation."""
    try:
        fn(*args)
    except Exception:
        logger.exception("metrics_mutation_failed")
        try:
            from src.common.metrics import qb_metrics_mutation_failed_total

            qb_metrics_mutation_failed_total.inc()
        except Exception:
            logger.exception("metrics_mutation_failure_count_failed")


def _count_safely(counter: Any, **labels: str) -> None:
    """라벨 생성과 증가를 **함께** 예외로부터 격리한다 (BL-536 R2).

    ★`.labels()` 도 감싸야 한다. multiprocess 모드에서 새 라벨 조합은 그 시점에
    mmap 파일을 늘리므로(디스크 full · 권한 오류 가능) **`.inc()` 만 감싸면 절반만
    막는 것**이다. 기존 선례(`order_service.py` 의 `record_metric_safely(gauge.inc)`)는
    라벨이 없는 gauge 라 그 구분이 없었다.

    기존 두 counter 의 호출 지점이 `try_claim_bar` 뒤 · 단일 commit 앞이라, 여기서 던지면
    claim 이 rollback 되고 다음 tick 이 같은 bar 를 다시 평가해 **매-tick 크래시 루프**가 된다.
    """
    record_metric_safely(lambda: counter.labels(**labels).inc())


def _touch_safely(counter: Any, **labels: str) -> None:
    """라벨 조합을 **증가 없이** 실체화한다. `_count_safely` 의 무증분 형제.

    ★왜 `_count_safely` 를 못 쓰나 — 그쪽은 `.inc()` 한다. 초기화에서 1 을 올리면
    창 차분이 실제 발화 수보다 커져 **계측이 스스로 거짓말**을 한다.

    ★왜 raw `.labels()` 를 직접 쓰지 않나 — `test_live_conditional_divergence_labels`
    가 그 counter 에 대한 raw `.labels()` 를 **AST 로 금지**한다. 그 규율의 의도는
    "라벨 생성도 예외로부터 격리하라" 이고, 이 함수는 그 의도를 지키면서 증분만 뺀다.
    """
    record_metric_safely(lambda: counter.labels(**labels))


def _quarantine_corrupt_metrics(path: str) -> None:
    quarantined = 0
    for metric_file in Path(path).glob("*.db"):
        try:
            MmapedDict.read_all_values_from_file(str(metric_file))  # type: ignore[no-untyped-call]
        except FileNotFoundError:
            continue
        except Exception:
            for suffix in count(1):
                try:
                    metric_file.rename(
                        metric_file.with_name(f"{metric_file.name}.corrupt-{suffix}")
                    )
                    quarantined += 1
                    break
                except FileExistsError:
                    continue
                except Exception:
                    logger.exception(
                        "metrics_multiprocess_quarantine_failed", extra={"file": str(metric_file)}
                    )
                    break
    if quarantined:
        logger.warning("metrics_multiprocess_corrupt_files_quarantined count=%d", quarantined)


def _process_identifier() -> str:
    """파일명 안전성과 배포 전체 고유성을 만족하는 writer 식별자를 만든다."""
    return f"{_PROCESS_IDENTIFIER_PREFIX}-{os.getpid()}"


def configure_multiprocess() -> None:
    """애플리케이션 metric 생성 전에 Prometheus mmap value를 활성화한다."""
    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not path:
        return

    global _PROCESS_IDENTIFIER_PREFIX
    role = re.sub(r"[^A-Za-z0-9]", "", os.environ.get("QB_METRICS_ROLE", "")) or "app"
    hostname = re.sub(r"[^A-Za-z0-9]", "", os.environ.get("HOSTNAME", ""))
    _PROCESS_IDENTIFIER_PREFIX = f"{role}-{hostname}" if hostname else role
    os.makedirs(path, exist_ok=True)
    values.ValueClass = values.MultiProcessValue(  # type: ignore[no-untyped-call]
        process_identifier=_process_identifier
    )


def build_metrics_registry() -> CollectorRegistry | None:
    """공유 파일 registry를 만들고, 미설정이면 단일 프로세스 fallback을 유지한다."""
    global _METRICS_REGISTRY
    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not path:
        return None
    os.makedirs(path, exist_ok=True)
    if _METRICS_REGISTRY is not None:
        return _METRICS_REGISTRY

    registry = CollectorRegistry()
    MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    GCCollector(registry)
    PlatformCollector(registry)
    ProcessCollector(registry=registry)
    _METRICS_REGISTRY = registry
    return registry


def render_metrics() -> bytes:
    """모든 프로세스 metric을 렌더하고 단일 프로세스 registry로 fallback한다."""
    from src.common import metrics as _metrics

    try:
        registry = build_metrics_registry()
        return generate_latest(registry) if registry is not None else generate_latest()
    except Exception:
        logger.exception("metrics_multiprocess_render_failed")
        global _METRICS_REGISTRY
        _METRICS_REGISTRY = None
        _metrics.qb_metrics_render_fallback_total.inc()
        path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
        if path:
            _quarantine_corrupt_metrics(path)
        return generate_latest()


def mark_metrics_process_dead() -> None:
    """현재 프로세스의 live gauge mmap 파일만 제거한다."""
    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return
    mark_process_dead(_process_identifier())  # type: ignore[no-untyped-call]


def reset_metrics_registry() -> None:
    """단위 테스트를 위해 캐시된 collector registry를 비운다."""
    global _METRICS_REGISTRY
    _METRICS_REGISTRY = None

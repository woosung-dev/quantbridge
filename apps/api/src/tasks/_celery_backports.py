# Celery 5.6.x prefork 풀의 broker 재연결 결함을 상류 수정과 같은 방식으로 메운다
"""[BL-870] ⑵ — `AsynPool.flush()` 백포트.

broker 연결이 끊기면 `Consumer.on_close()` 가 `AsynPool.flush()` 를 부르고, 5.6.3 의 flush 는
마지막에 `_busy_workers.clear()` 를 한다. 수락된 태스크를 아직 실행 중인 자식 프로세스까지
「한가함」이 되고, fair 스케줄러는 `_busy_workers` 만 보고 쓰기 대상을 고르므로 재연결 뒤 새
태스크를 **무한히 도는 스트림 프로세스의 입력 파이프에** 넣을 수 있다. 그 태스크는 `reserved`
에 머문 채 영원히 시작되지 않는다(2026-10-02 서버 ws-stream 실측).

상류 수정 = celery/celery#10346(2026-06-10 병합) — `clear()` 대신 「살아 있고 수락된 job 을
실행 중인 자식」으로 집합을 줄인다. 이 모듈은 그 결과를 flush 바깥에서 같은 규칙으로 복원한다.
★상류 수정이 든 첫 안정판(5.7)으로 올리면 `apply_asynpool_flush_backport` 는 아무것도 하지
않는다 — 그때 이 모듈과 호출 한 줄을 지워라.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import celery
from celery.concurrency import asynpool

_FIXED_IN = (5, 7)
_MARKER = "_qb_bl870_backport"


def _accepted_live_inqueue_fds(pool: Any) -> set[int]:
    """수락된 job 을 실행 중이고 살아 있는 자식의 inqueue write-fd (상류 `still_busy`)."""
    still_busy: set[int] = set()
    for job in pool._cache.values():
        if not job._accepted:
            continue
        proc = job._write_to or job._scheduled_for
        if proc is not None and proc._is_alive():
            still_busy.add(proc.inqW_fd)
    return still_busy


def _keep_busy_workers(original: Callable[[Any], None]) -> Callable[[Any], None]:
    def flush(self: Any) -> None:
        busy_before = set(self._busy_workers)
        original(self)
        # 원본은 마지막에 `_busy_workers.clear()` 를 한다. 상류는 clear 대신
        # `intersection_update(still_busy)` 이므로 결과 = 이전 집합 ∩ still_busy.
        self._busy_workers.update(busy_before & _accepted_live_inqueue_fds(self))

    setattr(flush, _MARKER, True)
    flush.__wrapped__ = original  # type: ignore[attr-defined]
    return flush


def apply_asynpool_flush_backport() -> bool:
    """패치를 걸었으면 True. 상류 수정이 든 버전이거나 이미 걸려 있으면 False."""
    if tuple(celery.VERSION[:2]) >= _FIXED_IN:
        return False
    if getattr(asynpool.AsynPool.flush, _MARKER, False):
        return False
    asynpool.AsynPool.flush = _keep_busy_workers(asynpool.AsynPool.flush)
    return True

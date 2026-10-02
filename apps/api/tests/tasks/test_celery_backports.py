# AsynPool.flush 백포트가 broker 재연결 뒤에도 실행 중인 자식을 「바쁨」으로 남기는지 검증한다

"""[BL-870] ⑵ 회귀 — `src/tasks/_celery_backports.py`.

케이스 1~5 는 상류 수정(celery/celery#10346)의 단위 테스트를 그대로 옮겼다. 실제 `AsynPool` 에
가짜 job 을 넣고 `flush()` 뒤의 `_busy_workers` 를 본다. 6 은 설치된 Celery 원본이 아직 결함을
가졌는지 재는 카나리다 — 이것이 실패하면 상류 수정이 들어온 것이니 백포트를 지울 때다.

실프로세스 재현(전용 redis 재시작 · 운영 이미지 · 3회 반복)은 `apps/api/scripts/repro_bl870_broker_reconnect.py` 가 갖는다.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
from unittest.mock import Mock, patch

import celery
import pytest
from celery.concurrency import asynpool

from src.tasks import _celery_backports
from src.tasks._celery_backports import apply_asynpool_flush_backport


@pytest.fixture(autouse=True)
def _backport_applied() -> None:
    apply_asynpool_flush_backport()


def _proc(fd: int, *, alive: bool = True) -> Mock:
    proc = Mock(name=f"proc{fd}")
    proc.inqW_fd = fd
    proc._is_alive.return_value = alive
    return proc


def _job(*, accepted: bool, write_to: Mock | None, scheduled_for: Mock | None) -> Mock:
    job = Mock(name="job")
    job._accepted = accepted
    job._write_to = write_to
    job._scheduled_for = scheduled_for
    job._writer.return_value = None
    return job


def _flushed(cache: dict[int, Mock], busy: set[int], flush=None) -> set[int]:
    with patch("billiard.pool.Pool._create_worker_process"):
        pool = asynpool.AsynPool(processes=2, synack=False, threads=False)
    pool._state = asynpool.RUN
    pool.maintain_pool = Mock(name="maintain_pool")
    pool._cache = cache
    pool._busy_workers = busy
    pool._active_writers.clear()
    pool.outbound_buffer.clear()
    (flush or asynpool.AsynPool.flush)(pool)
    return pool._busy_workers


def test_flush_keeps_worker_busy_while_it_runs_an_accepted_job() -> None:
    proc = _proc(7)
    assert 7 in _flushed({1: _job(accepted=True, write_to=proc, scheduled_for=proc)}, {7})


def test_flush_falls_back_to_scheduled_for_when_write_to_is_unset() -> None:
    proc = _proc(5)
    assert 5 in _flushed({1: _job(accepted=True, write_to=None, scheduled_for=proc)}, {5})


def test_flush_releases_worker_whose_job_was_never_accepted() -> None:
    proc = _proc(9)
    assert 9 not in _flushed({1: _job(accepted=False, write_to=proc, scheduled_for=proc)}, {9})


def test_flush_resolves_accepted_and_unaccepted_in_one_call() -> None:
    busy = _flushed(
        {
            1: _job(accepted=True, write_to=_proc(7), scheduled_for=_proc(7)),
            2: _job(accepted=False, write_to=_proc(9), scheduled_for=_proc(9)),
        },
        {7, 9},
    )
    assert busy == {7}


def test_flush_releases_worker_whose_process_died() -> None:
    proc = _proc(3, alive=False)
    assert 3 not in _flushed({1: _job(accepted=True, write_to=proc, scheduled_for=proc)}, {3})


@pytest.mark.skipif(
    tuple(celery.VERSION[:2]) >= (5, 7), reason="상류 수정이 든 버전 — 백포트를 지워라"
)
def test_installed_celery_flush_still_clears_busy_workers() -> None:
    """카나리 — 원본 flush 는 실행 중인 자식까지 한가함으로 만든다(= 백포트가 아직 필요하다)."""
    original = asynpool.AsynPool.flush.__wrapped__  # type: ignore[attr-defined]
    proc = _proc(7)
    assert (
        _flushed({1: _job(accepted=True, write_to=proc, scheduled_for=proc)}, {7}, original)
        == set()
    )


def test_backport_is_skipped_on_celery_with_the_upstream_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 원본으로 되돌려 둔다 — 안 그러면 「이미 걸림」 분기가 False 를 내서 버전 판정을 못 잰다.
    original = getattr(asynpool.AsynPool.flush, "__wrapped__", asynpool.AsynPool.flush)
    monkeypatch.setattr(asynpool.AsynPool, "flush", original)
    monkeypatch.setattr(_celery_backports.celery, "VERSION", (5, 7, 0, "", ""))
    assert apply_asynpool_flush_backport() is False
    assert asynpool.AsynPool.flush is original


def test_backport_is_applied_once() -> None:
    assert getattr(asynpool.AsynPool.flush, "_qb_bl870_backport", False) is True
    assert apply_asynpool_flush_backport() is False


def test_celery_app_import_applies_the_backport() -> None:
    """배선 — 새 프로세스에서 celery_app 만 import 한다(이 파일의 픽스처가 건 패치와 무관하게)."""
    code = (
        "import src.tasks.celery_app\n"
        "from celery.concurrency import asynpool\n"
        "print(getattr(asynpool.AsynPool.flush, '_qb_bl870_backport', False))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=pathlib.Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().splitlines()[-1] == "True"

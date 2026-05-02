"""Sprint 19 BL-081 — `qb_pending_alerts` gauge + `track_pending_alert()` 회귀.

codex G.0 P1 #4 (Sprint 19): drain + done_callback 중복 dec 방어. helper 가
idempotent — set membership 검사로 두 번째 dec 차단.

Sprint 18 Option C 의 cross-task semantic 명시 — fire-and-forget alert task
가 Celery task 경계 넘어 살아있을 때 gauge 가 정확한 in-flight count 표시.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Iterator

import pytest

from src.common import alert as alert_mod
from src.common.alert import track_pending_alert
from src.common.metrics import qb_pending_alerts


@pytest.fixture(autouse=True)
def _reset_alert_set_and_gauge() -> Iterator[None]:
    """매 test 시작/끝 — set + gauge 초기화 (다른 test 누수 방지)."""
    # gauge 는 process-wide singleton — 본 test 안에서만 사용 보장 위해 reset.
    # 직접 setter 없어 inc/dec 으로 0 으로 만들 수도 있지만, set drain 만으로
    # done_callback 트리거되어 gauge 가 0 으로 수렴 (idempotent helper 보장).
    for task in list(alert_mod._PENDING_ALERTS):
        if not task.done():
            task.cancel()
    alert_mod._PENDING_ALERTS.clear()
    qb_pending_alerts._value.set(0)  # type: ignore[attr-defined]
    yield
    for task in list(alert_mod._PENDING_ALERTS):
        if not task.done():
            task.cancel()
    alert_mod._PENDING_ALERTS.clear()
    qb_pending_alerts._value.set(0)  # type: ignore[attr-defined]


def _gauge_value() -> int:
    return int(qb_pending_alerts._value.get())  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_track_pending_alert_increments_gauge_and_set() -> None:
    """track 시 set add + gauge inc."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def _slow_alert() -> None:
        started.set()
        await release.wait()

    task = asyncio.create_task(_slow_alert())
    track_pending_alert(task)
    await started.wait()  # task 가 실제 await 진입했는지

    assert task in alert_mod._PENDING_ALERTS
    assert _gauge_value() == 1

    release.set()
    await task
    # done_callback 이 발화되어 set discard + gauge dec
    await asyncio.sleep(0)  # callback 처리 시간

    assert task not in alert_mod._PENDING_ALERTS
    assert _gauge_value() == 0


@pytest.mark.asyncio
async def test_track_pending_alert_handles_immediately_completed_task() -> None:
    """이미 완료된 task 도 정상 처리 — done_callback 즉시 발화 후 gauge 0 복귀."""

    async def _instant() -> None:
        return None

    task = asyncio.create_task(_instant())
    await task  # 미리 완료

    track_pending_alert(task)
    # add_done_callback 은 이미 done 한 task 면 즉시 호출 (next event loop iter)
    await asyncio.sleep(0)

    # 결과: 1번 inc + 1번 dec → 0
    assert task not in alert_mod._PENDING_ALERTS
    assert _gauge_value() == 0


@pytest.mark.asyncio
async def test_track_pending_alert_double_call_is_idempotent() -> None:
    """동일 task 에 두 번 호출 — set 가 두 번째를 흡수, gauge 도 1 만 증가."""
    release = asyncio.Event()

    async def _wait() -> None:
        await release.wait()

    task = asyncio.create_task(_wait())
    track_pending_alert(task)
    track_pending_alert(task)  # 두 번째 호출 — set membership 검사로 흡수

    assert _gauge_value() == 1, "double track 시 gauge 가 1만 inc 해야 함"

    release.set()
    await task
    await asyncio.sleep(0)

    assert _gauge_value() == 0


@pytest.mark.asyncio
async def test_drain_after_external_discard_does_not_underflow_gauge() -> None:
    """**codex G.0 P1 #4 fix 회귀 방어**.

    외부에서 `_PENDING_ALERTS.discard(task)` 호출 후 task 완료 시 done_callback
    이 발화. helper 의 idempotent 검사로 gauge 두 번째 dec 안 됨 → 음수 회피.
    """
    release = asyncio.Event()

    async def _wait() -> None:
        await release.wait()

    task = asyncio.create_task(_wait())
    track_pending_alert(task)
    assert _gauge_value() == 1

    # 외부 drain — set 에서 직접 제거 (e.g., shutdown 시)
    alert_mod._PENDING_ALERTS.discard(task)
    # gauge 는 helper 가 자동 dec 안 함 — drain 호출자 책임이지만 본 test 는
    # 외부 drain 후 done_callback 의 idempotent 검증에 집중.

    release.set()
    await task
    await asyncio.sleep(0)

    # done_callback 발화: task 가 set 에 없으므로 dec 호출 안 함 — gauge 변화 없음.
    # gauge 는 1 그대로 (외부 drain 이 dec 안 했으므로).
    assert _gauge_value() == 1, (
        "외부 drain 후 done_callback 이 두 번째 dec 발화 시 gauge underflow → 0 또는 음수"
    )


@pytest.mark.asyncio
async def test_track_pending_alert_with_cancelled_task() -> None:
    """task 가 cancel 되어도 done_callback 발화 → gauge 정상 dec."""

    async def _wait() -> None:
        await asyncio.sleep(60)  # 절대 release 안 됨

    task = asyncio.create_task(_wait())
    track_pending_alert(task)
    assert _gauge_value() == 1

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)

    assert task not in alert_mod._PENDING_ALERTS
    assert _gauge_value() == 0

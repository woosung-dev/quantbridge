"""Beat schedule 등록 검증 — reclaim_stale_running_task 5분 주기."""
from src.tasks import backtest as _backtest  # noqa: F401 — task 등록 강제
from src.tasks import celery_app  # type: ignore[attr-defined]
from src.tasks import optimizer_tasks as _optimizer  # noqa: F401 — task 등록 강제
from src.tasks import stress_test_tasks as _stress  # noqa: F401 — task 등록 강제


def test_reclaim_stale_beat_registered() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "reclaim-stale-backtests" in schedule
    entry = schedule["reclaim-stale-backtests"]
    assert entry["task"] == "backtest.reclaim_stale"
    assert entry["schedule"] == 300.0
    assert entry["options"]["expires"] == 240


def test_reclaim_stale_task_registered() -> None:
    """Celery task가 broker registry에 등록되어 있는지 확인.

    src.tasks.backtest를 명시적으로 import해야 데코레이터가 실행되어 등록됨
    (worker는 celery include로 자동 import, test는 수동).
    """
    assert "backtest.reclaim_stale" in celery_app.tasks


# CF3 (Phase C-1) — optimizer/stress_test 도 동일 reclaim watchdog 등록.
def test_optimizer_reclaim_stale_registered() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "reclaim-stale-optimizations" in schedule
    entry = schedule["reclaim-stale-optimizations"]
    assert entry["task"] == "optimizer.reclaim_stale"
    assert entry["schedule"] == 300.0
    assert entry["options"]["expires"] == 240
    assert "optimizer.reclaim_stale" in celery_app.tasks


def test_stress_test_reclaim_stale_registered() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "reclaim-stale-stress-tests" in schedule
    entry = schedule["reclaim-stale-stress-tests"]
    assert entry["task"] == "stress_test.reclaim_stale"
    assert entry["schedule"] == 300.0
    assert entry["options"]["expires"] == 240
    assert "stress_test.reclaim_stale" in celery_app.tasks

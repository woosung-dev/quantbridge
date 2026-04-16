"""Beat schedule 등록 검증 — reclaim_stale_running_task 5분 주기."""
from src.tasks import backtest as _backtest  # noqa: F401 — task 등록 강제
from src.tasks import celery_app  # type: ignore[attr-defined]


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

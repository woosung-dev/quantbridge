"""Python 연구 작업의 비동기 원장 처리. 코드는 전용 runner에서만 실행한다."""

from uuid import UUID

from src.tasks._worker_engine import create_worker_engine_and_sm
from src.tasks._worker_loop import run_in_worker_loop
from src.tasks.celery_app import celery_app


@celery_app.task(name="python_strategy.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_python_backtest_task(run_id: str) -> None:
    run_in_worker_loop(execute(UUID(run_id)))


async def execute(run_id: UUID) -> None:
    from src.python_strategy.dependencies import build_service_for_worker

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            await build_service_for_worker(session).execute(run_id)
    finally:
        await engine.dispose()


@celery_app.task(name="python_strategy.reclaim_stale", max_retries=0)  # type: ignore[untyped-decorator]
def reclaim_python_backtests() -> int:
    return run_in_worker_loop(reclaim())


async def reclaim() -> int:
    from src.python_strategy.repository import PythonStrategyRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = PythonStrategyRepository(session)
            count = await repo.reclaim_stale()
            await repo.commit()
            return count
    finally:
        await engine.dispose()

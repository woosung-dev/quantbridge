# Celery prefork worker 전용 prefork-safe async engine factory SSOT.
"""Prefork-safe async engine + sessionmaker factory.

Celery prefork 워커는 매 task 마다 `asyncio.run()` 으로 새 event loop 를 만든다.
asyncpg connection pool 은 생성 당시 loop 에 bind 되므로, 전역 engine 을 캐시해
두면 두 번째 task 부터 "got Future attached to a different loop" → 이후 pool 이
깨져 "another operation is in progress" 가 연쇄된다. 따라서 engine /
sessionmaker 는 _execute / reclaim 내부에서 **매 호출마다 새로 만들고
dispose** 해야 한다.

Sprint 59 PR-A — 본 모듈 신설 이전에는 8 개 task 파일이 동일 함수를 각각
정의 (Sprint 18 BL-080) 했으나, 사본 drift 위험 + LESSON-038 worker rebuild
sentinel 단순화를 위해 단일 SSOT 로 통합.

Sprint 18 BL-080 prefork-safe pattern 의 핵심 의무:
1. 매 호출마다 새 engine + sessionmaker 반환.
2. caller 는 finally 에서 `await engine.dispose()` 의무 (`_worker_loop.py` 가
   대신 처리하는 경우 호출자 책임 0).
3. 테스트는 본 함수를 monkeypatch 로 대체하여 공유 세션 / no-op engine 주입.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings


def create_worker_engine_and_sm() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """매 호출마다 새 engine + async_sessionmaker 튜플 반환.

    호출자는 반환된 engine 을 finally 에서 dispose 해야 한다.
    테스트에서는 본 함수를 monkeypatch 로 대체하여 공유 세션 / no-op engine
    주입 가능.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm

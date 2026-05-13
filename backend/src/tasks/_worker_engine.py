# Celery prefork worker 안전 engine + sessionmaker factory (Sprint 18 BL-080 Option C).
"""Per-task engine 생성 helper — prefork-safe 패턴 단일 SSOT.

Celery prefork 워커는 매 task 마다 asyncio.run() 으로 새 event loop 를 만든다.
asyncpg connection pool 은 생성 당시 loop 에 bind 되므로, 전역 engine 캐시 시
2nd task 부터 ``got Future attached to a different loop`` + 이후
``another operation is in progress`` 연쇄 실패 (PR #51 / BL-080 Sprint 18 root cause).

따라서 engine/sessionmaker 는 각 ``_async_*`` 진입 시 매번 새로 생성하고
finally 에서 ``await engine.dispose()`` 의무 (`.ai/stacks/fastapi/backend.md §9.3`).

호출자는 본 함수 반환 engine 을 try/finally 로 dispose 해야 한다.
테스트는 본 함수를 monkeypatch 로 대체 가능 (공유 세션 / no-op engine).
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
    """매 호출마다 새 engine + async_sessionmaker 튜플 반환 (prefork-safe).

    표준 reference: ``.ai/stacks/fastapi/backend.md §9.3``. 호출자는 finally 에서
    ``await engine.dispose()`` 의무 (connection pool stale connection 누수 방어).
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm

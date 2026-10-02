# 워커 엔진이 서버 쪽에서 끊긴 풀 연결을 다시 잇는지 실 DB 로 검증한다

"""[BL-870] ⑴ 회귀.

2026-10-02 서버에서 db 컨테이너만 재생성하자 ws-stream 의 public ticker 태스크가
60초 심볼 refresh 에서 `InterfaceError: connection is closed` 로 죽었다. 태스크 단위
엔진(`create_worker_engine_and_sm`)이 재생성 전에 맺어 풀에 돌려 둔 연결을 그대로
다시 꺼냈기 때문이다. API 엔진(`src/common/database.py`)은 `pool_pre_ping=True` 라
같은 상황에서 다시 붙는다.

판별력 — 풀에 돌아간 연결의 백엔드를 `pg_terminate_backend` 로 끊고, 그 프로세스가
사라진 것을 확인한 뒤 같은 엔진으로 다시 조회한다. pre-ping 이 없으면 두 번째 조회가
`connection is closed` 로 죽는다(수정 전 실측 red).
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import settings
from src.tasks._worker_engine import create_worker_engine_and_sm
from tests import _db_guard


async def test_worker_engine_reconnects_after_server_side_disconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dsn = _db_guard.effective_dsn()
    monkeypatch.setattr(settings, "database_url", SecretStr(dsn))
    engine, sm = create_worker_engine_and_sm()
    killer = create_async_engine(dsn, poolclass=NullPool)
    try:
        async with sm() as session:
            pid = (await session.execute(text("SELECT pg_backend_pid()"))).scalar_one()

        async with killer.connect() as conn:
            terminated = (
                await conn.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
            ).scalar_one()
            assert terminated is True
            # 종료 신호만 보내고 끝나면 pre-ping 이 아직 살아 있는 백엔드에 닿아 통과할 수 있다.
            for _ in range(100):
                alive = (
                    await conn.execute(
                        text("SELECT count(*) FROM pg_stat_activity WHERE pid = :pid"),
                        {"pid": pid},
                    )
                ).scalar_one()
                if alive == 0:
                    break
                await asyncio.sleep(0.05)
            else:
                pytest.fail(f"백엔드 {pid} 가 5초 안에 종료되지 않았다")

        async with sm() as session:
            new_pid = (await session.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        assert new_pid != pid
    finally:
        await killer.dispose()
        await engine.dispose()

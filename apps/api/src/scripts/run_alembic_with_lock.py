"""Sprint 30 ε B6 — Alembic upgrade head with PostgreSQL advisory lock.

다중 인스턴스 cold start 시 동시 migration race 차단.

Flow:
1. asyncpg 로 DATABASE_URL 연결.
2. ``pg_try_advisory_lock(<key>)`` 으로 lock 획득 시도.
3. 실패 시 ``--timeout`` 초까지 1s 간격 재시도.
4. lock 획득 → ``alembic upgrade head`` 실행 (asyncio.create_subprocess_exec).
5. session close 와 함께 advisory lock 자동 해제 (session-level lock).

CLI:
    python -m src.scripts.run_alembic_with_lock --lock-key 1903723824 --timeout 30

사용처:
- ``backend/docker-entrypoint.sh`` 의 ``run_alembic_with_lock()`` shell 함수.

설계 결정:
- ``pg_try_advisory_lock`` (non-blocking) + sleep loop. ``pg_advisory_lock``
  (blocking) 은 stalled migration 시 무한 대기 가능 → SLO 위반.
- ``asyncio.create_subprocess_exec`` 로 alembic 호출 — alembic env.py 가 자체
  async engine 생성하여 우리 lock 세션과 충돌 회피.
- lock release 는 session close 시 자동 — explicit ``pg_advisory_unlock`` 불필요.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


def _normalize_url_for_asyncpg(database_url: str) -> str:
    """asyncpg 가 받을 수 있는 URL 로 정규화.

    SQLAlchemy 의 ``postgresql+asyncpg://`` prefix 제거.
    그 외 (``postgresql://`` / ``postgres://``) 는 그대로.
    """
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url


async def _acquire_advisory_lock(
    database_url: str, lock_key: int, timeout_s: int
) -> asyncpg.Connection[asyncpg.Record]:
    """advisory lock 획득. asyncpg connection 반환 (lock 보유 중).

    timeout_s 안에 못 잡으면 RuntimeError. 호출자가 connection close 책임.
    """
    import asyncpg as _asyncpg

    pg_url = _normalize_url_for_asyncpg(database_url)
    deadline = asyncio.get_event_loop().time() + timeout_s
    conn = await _asyncpg.connect(pg_url)
    try:
        while True:
            acquired = await conn.fetchval(
                "SELECT pg_try_advisory_lock($1::bigint)", lock_key
            )
            if acquired:
                logger.info("alembic_advisory_lock_acquired key=%d", lock_key)
                return conn
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise RuntimeError(
                    f"Advisory lock {lock_key} not acquired within {timeout_s}s"
                )
            logger.info(
                "alembic_advisory_lock_wait key=%d remaining_s=%.1f",
                lock_key,
                remaining,
            )
            await asyncio.sleep(1.0)
    except Exception:
        await conn.close()
        raise


async def _run_alembic_upgrade_head() -> int:
    """``alembic upgrade head`` 를 asyncio subprocess 로 실행.

    Returns subprocess returncode (0 = 성공).
    """
    logger.info("alembic_upgrade_head_start")
    proc = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alembic",
        "upgrade",
        "head",
    )
    rc = await proc.wait()
    logger.info("alembic_upgrade_head_done rc=%d", rc)
    return rc


async def run(lock_key: int, timeout_s: int) -> int:
    """advisory lock 획득 후 ``alembic upgrade head`` 실행.

    Returns:
        subprocess returncode (0 = 성공).

    Raises:
        RuntimeError: lock acquire timeout.
    """
    from src.core.config import settings

    database_url = settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL not configured")

    conn = await _acquire_advisory_lock(database_url, lock_key, timeout_s)
    try:
        return await _run_alembic_upgrade_head()
    finally:
        try:
            await conn.close()  # session close → lock auto release
        except Exception as exc:
            logger.warning("alembic_advisory_lock_close_failed err=%s", exc)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_alembic_with_lock",
        description="Run `alembic upgrade head` under a PostgreSQL advisory lock.",
    )
    parser.add_argument(
        "--lock-key",
        type=int,
        default=1903723824,
        help="64-bit advisory lock key (default 1903723824 = 0x71626730 'qbg0').",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Max seconds to wait for the lock (default 30).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        rc = asyncio.run(run(args.lock_key, args.timeout))
    except RuntimeError as exc:
        logger.error("alembic_advisory_lock_failed %s", exc)
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())

"""Sprint 25 BL-110a — In-process WS lease integration test.

격리 stack Redis (6380) 실 hit. 6 시나리오:
1. 실 Redis 에 lease acquire → WsLease 반환 + Redis key 존재
2. 동일 account 두 번째 acquire → None (lease 점유)
3. account 격리 (다른 account 는 동시 acquire OK)
4. heartbeat extend → True → lost_event 미set
5. heartbeat extend → False mock → lost_event.set + heartbeat 종료 (codex G.0 iter 2 P1 #8 critical)
6. __aexit__ → Redis key 부재 (Lua CAS DEL 검증)

`@pytest.mark.integration` + `--run-integration` flag — default skip. 격리 stack 가동 시만.

본 sprint 는 in-process 만 (BL-110a). real Celery prefork SIGTERM (BL-110b) 은 Sprint 26+
(pytest-celery 또는 subprocess.Popen 으로 worker 부팅 후 SIGTERM 검증).
"""
from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest

from src.common.redis_client import get_redis_lock_pool, reset_redis_lock_pool
from src.common.redlock import RedisLock
from src.tasks._ws_lease import (
    WsLease,
    _lease_key,
    acquire_ws_lease,
    is_lease_active,
)

pytestmark = pytest.mark.integration


def _unique_account_id() -> str:
    """test 마다 고유 account id — 다른 test 와 lease key 충돌 방지."""
    return f"test-acct-{uuid.uuid4().hex[:12]}"


@pytest.fixture(autouse=True)
def _reset_pool_each_test() -> Generator[None, None, None]:
    """매 test 진입 전 pool reset — pytest-asyncio 의 per-test event loop 와
    redis-py asyncio connection bound 충돌 회피.
    """
    reset_redis_lock_pool()
    yield
    reset_redis_lock_pool()


@pytest.fixture
async def cleanup_lease_keys() -> AsyncGenerator[list[str], None]:
    """test 종료 후 사용한 모든 lease key 삭제 (다른 test fixture 영향 차단)."""
    used_keys: list[str] = []
    yield used_keys
    pool = get_redis_lock_pool()
    for key in used_keys:
        with contextlib.suppress(Exception):
            await pool.delete(_lease_key(key))


@pytest.mark.asyncio
async def test_acquire_real_redis_returns_lease(
    cleanup_lease_keys: list[str],
) -> None:
    """실 Redis 에 acquire 성공 → WsLease 반환 + key 존재."""
    account_id = _unique_account_id()
    cleanup_lease_keys.append(account_id)

    lease = await acquire_ws_lease(account_id, ttl_ms=5_000)

    assert lease is not None
    assert isinstance(lease, WsLease)
    assert await is_lease_active(account_id) is True

    # cleanup — release lease
    async with lease:
        pass


@pytest.mark.asyncio
async def test_duplicate_acquire_returns_none(
    cleanup_lease_keys: list[str],
) -> None:
    """동일 account 두 번째 acquire → None (lease 점유)."""
    account_id = _unique_account_id()
    cleanup_lease_keys.append(account_id)

    lease_a = await acquire_ws_lease(account_id, ttl_ms=5_000)
    assert lease_a is not None

    # 두 번째 acquire 시도 — None 반환
    lease_b = await acquire_ws_lease(account_id, ttl_ms=5_000)
    assert lease_b is None

    # cleanup
    async with lease_a:
        pass


@pytest.mark.asyncio
async def test_account_isolation(cleanup_lease_keys: list[str]) -> None:
    """다른 account 는 동시 acquire 가능 (lease key 격리)."""
    account_a = _unique_account_id()
    account_b = _unique_account_id()
    cleanup_lease_keys.extend([account_a, account_b])

    lease_a = await acquire_ws_lease(account_a, ttl_ms=5_000)
    lease_b = await acquire_ws_lease(account_b, ttl_ms=5_000)

    assert lease_a is not None
    assert lease_b is not None

    # cleanup
    async with lease_a:
        pass
    async with lease_b:
        pass


@pytest.mark.asyncio
async def test_heartbeat_extend_success_keeps_lost_event_clear(
    cleanup_lease_keys: list[str],
) -> None:
    """heartbeat extend 성공 (실 Redis) → lost_event 미set."""
    account_id = _unique_account_id()
    cleanup_lease_keys.append(account_id)

    # ttl_ms=300ms → heartbeat interval = 100ms. 0.4s 동안 3-4 cycle 발생.
    lease = await acquire_ws_lease(account_id, ttl_ms=300)
    assert lease is not None

    async with lease:
        await asyncio.sleep(0.4)
        assert lease.lost_event.is_set() is False


@pytest.mark.asyncio
async def test_heartbeat_extend_false_sets_lost_event(
    cleanup_lease_keys: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex G.0 iter 2 P1 #8 critical — `extend()` falsy return 시 lost_event.set.

    `_heartbeat_loop` 가 exception 잡지 않음. extend() False return 시만 lost_event set.
    `extend → False` mock 으로 split-brain 차단 path 검증.
    """
    account_id = _unique_account_id()
    cleanup_lease_keys.append(account_id)

    lease = await acquire_ws_lease(account_id, ttl_ms=300)
    assert lease is not None

    # monkeypatch RedisLock.extend → 항상 False (token mismatch 시뮬)
    async def fake_extend(self: RedisLock, ttl_ms: int) -> bool:
        return False

    monkeypatch.setattr(RedisLock, "extend", fake_extend)

    async with lease:
        # codex G.2 P2 #12 — sleep 기반 flaky 회피 (asyncio.wait_for + lost_event.wait)
        await asyncio.wait_for(lease.lost_event.wait(), timeout=1.0)
        assert lease.lost_event.is_set() is True


@pytest.mark.asyncio
async def test_heartbeat_extend_exception_sets_lost_event(
    cleanup_lease_keys: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sprint 25 codex G.2 P1 #2 fix — `extend()` exception 시 lost_event.set 보장.

    이전 코드는 falsy return 만 set, exception 시 heartbeat task 만 종료 + stream 계속
    → split-brain 위험. 본 test 가 Redis timeout 시뮬 (RuntimeError raise) → lost_event
    set 검증.
    """
    account_id = _unique_account_id()
    cleanup_lease_keys.append(account_id)

    lease = await acquire_ws_lease(account_id, ttl_ms=300)
    assert lease is not None

    # monkeypatch RedisLock.extend → exception (Redis timeout 시뮬)
    async def fake_extend_raises(self: RedisLock, ttl_ms: int) -> bool:
        raise RuntimeError("Redis connection reset")

    monkeypatch.setattr(RedisLock, "extend", fake_extend_raises)

    async with lease:
        # asyncio.wait_for + lost_event.wait 로 flaky 회피 (codex G.2 P2 #12 권장)
        await asyncio.wait_for(lease.lost_event.wait(), timeout=1.0)
        assert lease.lost_event.is_set() is True


@pytest.mark.asyncio
async def test_aexit_releases_redis_key(cleanup_lease_keys: list[str]) -> None:
    """`__aexit__` 후 Redis key 부재 (Lua CAS DEL 검증)."""
    account_id = _unique_account_id()
    cleanup_lease_keys.append(account_id)

    lease = await acquire_ws_lease(account_id, ttl_ms=5_000)
    assert lease is not None

    async with lease:
        # in-scope 동안 active
        assert await is_lease_active(account_id) is True

    # __aexit__ 후 key 부재
    assert await is_lease_active(account_id) is False

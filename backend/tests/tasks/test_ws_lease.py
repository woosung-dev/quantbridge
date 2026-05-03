"""Sprint 24 BL-011 — Redis WS lease + heartbeat tests.

codex G.0 P1 #1 verifier: RedisLock graceful degrade (acquired=False) 가
acquire_ws_lease() 에서 None 으로 변환 → stream 절대 시작 안 함.

Test Coverage:
- single account acquire 성공
- 동일 account 동시 시도 → 1 winner only (duplicate skip)
- heartbeat extend 호출 검증 (20s 마다, mock time)
- async CM __aexit__ 가 heartbeat cancel + lock release 보장
- Redis 장애 (RedisError) → None 반환 + skip
- lease key 충돌 isolation (account_a vs account_b)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tasks._ws_lease import (
    WsLease,
    _lease_key,
    acquire_ws_lease,
    is_lease_active,
)


@pytest.fixture
def fake_redis_pool():
    """Mock Redis pool with controllable SET NX behavior."""
    pool = MagicMock()
    pool.set = AsyncMock(return_value=True)  # default: acquire 성공
    pool.eval = AsyncMock(return_value=1)  # default: extend / unlock 성공
    pool.exists = AsyncMock(return_value=0)  # default: key 부재
    return pool


@pytest.mark.asyncio
async def test_acquire_ws_lease_success(fake_redis_pool) -> None:
    """첫 acquire 성공 → WsLease 인스턴스 반환."""
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        lease = await acquire_ws_lease("acct-1", ttl_ms=60_000)
    assert lease is not None
    assert isinstance(lease, WsLease)
    fake_redis_pool.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_ws_lease_contention_returns_none(fake_redis_pool) -> None:
    """codex G.0 P1 #1 verifier — contention (SET NX 실패) 시 None 반환.

    RedisLock.__aenter__() 의 graceful degrade (acquired=False) 가 None 으로 변환되어
    caller 가 stream 시작 안 함. 중복 stream 방지의 핵심.
    """
    fake_redis_pool.set = AsyncMock(return_value=None)  # contention 시뮬
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        lease = await acquire_ws_lease("acct-1", ttl_ms=60_000)
    assert lease is None


@pytest.mark.asyncio
async def test_acquire_ws_lease_redis_failure_returns_none(fake_redis_pool) -> None:
    """Redis 장애 (RedisError) 시 None 반환 — WS lease 는 fallback 없음."""
    fake_redis_pool.set = AsyncMock(side_effect=RuntimeError("Redis connection refused"))
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        lease = await acquire_ws_lease("acct-1", ttl_ms=60_000)
    assert lease is None


@pytest.mark.asyncio
async def test_ws_lease_async_cm_releases_lock_on_exit(fake_redis_pool) -> None:
    """async CM __aexit__ 가 RedisLock release (Lua CAS DEL) 보장."""
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        lease = await acquire_ws_lease("acct-1", ttl_ms=60_000)
        assert lease is not None
        async with lease:
            pass  # exit 즉시
    # eval 호출 = unlock (Lua CAS DEL)
    fake_redis_pool.eval.assert_awaited()


@pytest.mark.asyncio
async def test_ws_lease_heartbeat_extends_lock(fake_redis_pool) -> None:
    """heartbeat task 가 RedisLock.extend (Lua CAS PEXPIRE) 호출.

    TTL=60ms (매우 짧게) + heartbeat ratio=3 → 20ms 마다 extend.
    50ms 대기 → 최소 1회 이상 extend 호출.
    """
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        lease = await acquire_ws_lease("acct-1", ttl_ms=60)
        assert lease is not None
        async with lease:
            await asyncio.sleep(0.05)  # 50ms 대기
    # eval 호출 ≥ 2 (heartbeat extend × N + 종료 시 unlock)
    assert fake_redis_pool.eval.call_count >= 2


@pytest.mark.asyncio
async def test_ws_lease_heartbeat_cancelled_on_exit(fake_redis_pool) -> None:
    """__aexit__ 가 heartbeat task cancel — 누수 없음."""
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        lease = await acquire_ws_lease("acct-1", ttl_ms=60_000)
        assert lease is not None
        async with lease:
            assert lease._heartbeat_task is not None
            assert not lease._heartbeat_task.done()
        # exit 후 heartbeat None
        assert lease._heartbeat_task is None


@pytest.mark.asyncio
async def test_lease_key_isolation() -> None:
    """account_a 와 account_b 는 별도 lease key — Redis 충돌 없음."""
    assert _lease_key("acct-1") == "ws:lease:acct-1"
    assert _lease_key("acct-2") == "ws:lease:acct-2"
    assert _lease_key("acct-1") != _lease_key("acct-2")


@pytest.mark.asyncio
async def test_is_lease_active_returns_true_when_key_exists(fake_redis_pool) -> None:
    """Reconcile path (codex P2 #1) — lease key 존재 → active=True."""
    fake_redis_pool.exists = AsyncMock(return_value=1)
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        active = await is_lease_active("acct-1")
    assert active is True


@pytest.mark.asyncio
async def test_is_lease_active_returns_false_when_key_missing(fake_redis_pool) -> None:
    """lease key 부재 → active=False (reconcile 가 enqueue)."""
    fake_redis_pool.exists = AsyncMock(return_value=0)
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        active = await is_lease_active("acct-1")
    assert active is False


@pytest.mark.asyncio
async def test_is_lease_active_redis_failure_returns_true(fake_redis_pool) -> None:
    """Redis 장애 시 보수적으로 active=True (reconcile enqueue skip)."""
    fake_redis_pool.exists = AsyncMock(side_effect=RuntimeError("Redis down"))
    with patch("src.common.redlock.get_redis_lock_pool", return_value=fake_redis_pool), patch("src.tasks._ws_lease.get_redis_lock_pool", return_value=fake_redis_pool):
        active = await is_lease_active("acct-1")
    assert active is True

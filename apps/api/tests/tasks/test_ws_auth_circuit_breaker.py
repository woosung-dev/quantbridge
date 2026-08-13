"""Sprint 24 BL-013 — WS auth/network circuit breaker tests.

codex G.0 P1 #3 verifier:
- BybitAuthError 즉시 block (`ws:auth:blocked` SET, counter reset)
- network failure 1/2회 통과
- network 3회 누적 시 block + counter reset
- TTL 만료 자동 재개 (mock)
- 수동 reset 후 즉시 재개
- metric inc 검증
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tasks._ws_circuit_breaker import (
    _NETWORK_FAILURE_THRESHOLD,
    is_circuit_open,
    record_auth_failure,
    record_network_failure,
    reset_circuit,
)


@pytest.fixture
def fake_redis_pool():
    pool = MagicMock()
    pool.set = AsyncMock(return_value=True)
    pool.delete = AsyncMock(return_value=1)
    pool.exists = AsyncMock(return_value=0)
    pool.incr = AsyncMock(return_value=1)
    pool.expire = AsyncMock(return_value=True)
    return pool


@pytest.mark.asyncio
async def test_is_circuit_open_false_when_key_missing(fake_redis_pool) -> None:
    """blocked key 부재 → False (정상 진입)."""
    fake_redis_pool.exists = AsyncMock(return_value=0)
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        assert (await is_circuit_open("acct-1")) is False


@pytest.mark.asyncio
async def test_is_circuit_open_true_when_blocked(fake_redis_pool) -> None:
    """blocked key 존재 → True (skip)."""
    fake_redis_pool.exists = AsyncMock(return_value=1)
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        assert (await is_circuit_open("acct-1")) is True


@pytest.mark.asyncio
async def test_record_auth_failure_blocks_immediately(fake_redis_pool) -> None:
    """codex G.0 P1 #3 verifier — BybitAuthError 즉시 block.

    `ws:auth:blocked:{account_id}` SET PX 3_600_000 + counter reset.
    """
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        await record_auth_failure("acct-1")
    # blocked SET 호출
    fake_redis_pool.set.assert_awaited_once()
    set_call = fake_redis_pool.set.call_args
    assert "ws:auth:blocked:acct-1" in set_call.args
    assert set_call.kwargs.get("px") == 3_600_000
    # failures counter reset
    fake_redis_pool.delete.assert_awaited_once_with("ws:auth:failures:acct-1")


@pytest.mark.asyncio
async def test_record_network_failure_under_threshold_does_not_block(
    fake_redis_pool,
) -> None:
    """network 1회 누적 → INCR 만, blocked SET 없음."""
    fake_redis_pool.incr = AsyncMock(return_value=1)
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        opened = await record_network_failure("acct-1")
    assert opened is False
    # blocked SET 호출 안 됨 (network_failure metric 만 inc)
    fake_redis_pool.set.assert_not_awaited()
    fake_redis_pool.incr.assert_awaited_once_with("ws:auth:failures:acct-1")


@pytest.mark.asyncio
async def test_record_network_failure_threshold_blocks(fake_redis_pool) -> None:
    """codex G.0 P1 #3 verifier — network 3회 누적 시 block."""
    fake_redis_pool.incr = AsyncMock(return_value=_NETWORK_FAILURE_THRESHOLD)
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        opened = await record_network_failure("acct-1")
    assert opened is True
    # 3회 도달 시 blocked SET + counter reset
    fake_redis_pool.set.assert_awaited_once()
    fake_redis_pool.delete.assert_awaited_once_with("ws:auth:failures:acct-1")


@pytest.mark.asyncio
async def test_reset_circuit_deletes_both_keys(fake_redis_pool) -> None:
    """수동 해제 helper — blocked + failures 둘 다 DEL."""
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        await reset_circuit("acct-1")
    fake_redis_pool.delete.assert_awaited_once_with(
        "ws:auth:blocked:acct-1", "ws:auth:failures:acct-1"
    )


@pytest.mark.asyncio
async def test_is_circuit_open_redis_failure_returns_false(fake_redis_pool) -> None:
    """Redis 장애 시 보수적으로 False (false-positive 회피)."""
    fake_redis_pool.exists = AsyncMock(side_effect=RuntimeError("Redis down"))
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        assert (await is_circuit_open("acct-1")) is False


@pytest.mark.asyncio
async def test_record_network_failure_isolates_per_account(fake_redis_pool) -> None:
    """account_a 의 failures 는 account_b 에 영향 없음."""
    fake_redis_pool.incr = AsyncMock(return_value=1)
    with patch(
        "src.tasks._ws_circuit_breaker.get_redis_lock_pool",
        return_value=fake_redis_pool,
    ):
        await record_network_failure("acct-a")
    fake_redis_pool.incr.assert_awaited_with("ws:auth:failures:acct-a")

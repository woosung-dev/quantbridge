"""Sprint 10 Phase A2 — RedisLock 10 TDD.

fakeredis.aioredis 를 사용해 실제 Redis 없이 단위 테스트.
실제 Redis integration 은 Phase C (real_broker) 에서 수행.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def fake_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """src.common.redis_client._pool 을 fakeredis.aioredis.FakeRedis 로 교체.

    Lua CAS 지원이 필요하므로 fakeredis[lua] (lupa) 사용.
    """
    import fakeredis.aioredis

    from src.common import redis_client as rc

    fake = fakeredis.aioredis.FakeRedis(decode_responses=False)
    rc._pool = fake  # type: ignore[assignment]
    try:
        yield fake
    finally:
        await fake.flushdb()
        try:
            await fake.aclose()
        except AttributeError:
            await fake.close()  # 구버전 fakeredis 호환
        rc._pool = None


# ---------------------------------------------------------------------------
# TDD 1: basic acquire + release
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_basic_acquire_and_release(fake_redis: AsyncMock) -> None:
    """SET NX 성공 → acquired=True. exit 시 Lua CAS DEL."""
    from src.common.redlock import RedisLock

    async with RedisLock("test:basic", ttl_ms=5000) as acquired:
        assert acquired is True
        stored = await fake_redis.get("test:basic")
        assert stored is not None  # key 가 실제로 세팅됨
    # exit 후 Lua CAS DEL → key 삭제
    assert await fake_redis.get("test:basic") is None


# ---------------------------------------------------------------------------
# TDD 2: contention (두 번째 acquire → False)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_contention(fake_redis: AsyncMock) -> None:
    """첫 번째 lock 이 key 점유 중이면 두 번째는 acquired=False."""
    from src.common.redlock import RedisLock

    first = RedisLock("test:cont", ttl_ms=5000)
    await first.__aenter__()
    assert first.acquired is True

    second = RedisLock("test:cont", ttl_ms=5000)
    got = await second.__aenter__()
    assert got is False
    assert second.acquired is False

    # 정리 — first 해제
    await first.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# TDD 3: TTL auto-release
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_ttl_auto_release(fake_redis: AsyncMock) -> None:
    """TTL 만료 후 동일 key 에 다른 워커가 획득 가능."""
    from src.common.redlock import RedisLock

    first = RedisLock("test:ttl", ttl_ms=50)  # 50ms
    await first.__aenter__()
    assert first.acquired is True

    await asyncio.sleep(0.12)  # 120ms — TTL 2.4배 여유

    second = RedisLock("test:ttl", ttl_ms=50)
    got = await second.__aenter__()
    assert got is True, "TTL 만료 후 재획득 가능해야"

    await second.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# TDD 4: unique-token CAS unlock (foreign token → DEL 거부)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_unlock_cas_rejects_foreign_token(fake_redis: AsyncMock) -> None:
    """다른 token 보유 시 unlock (DEL) 거부 — wrong-release 방지."""
    from src.common.redlock import RedisLock

    # first 획득
    first = RedisLock("test:cas", ttl_ms=5000)
    await first.__aenter__()
    assert first.acquired is True

    # TTL 만료 후 다른 워커 재획득 시뮬 — key 를 foreign-token 으로 직접 교체
    await fake_redis.set("test:cas", b"foreign-token", px=5000)

    # first 가 exit 해도 Lua CAS 가 token mismatch → DEL 거부
    await first.__aexit__(None, None, None)

    # key 는 여전히 foreign-token
    assert await fake_redis.get("test:cas") == b"foreign-token"


# ---------------------------------------------------------------------------
# TDD 5: Redis 미가용 → acquired=False (graceful degrade)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_unavailable_graceful_degrade() -> None:
    """Redis 장애 → acquired=False. raise 하지 않음."""
    from src.common import redis_client as rc

    orig_pool = rc._pool
    try:
        fake = AsyncMock()
        fake.set = AsyncMock(side_effect=ConnectionError("boom"))
        rc._pool = fake  # type: ignore[assignment]

        from src.common.redlock import RedisLock

        lock = RedisLock("test:unavail", ttl_ms=1000)
        got = await lock.__aenter__()
        assert got is False
        assert lock.acquired is False
    finally:
        rc._pool = orig_pool  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# TDD 6: mid-lock disconnect (extend/unlock silent fail, raise 없음)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_mid_lock_disconnect() -> None:
    """Lock 보유 중 Redis 연결 끊김 — extend/unlock 모두 silent fail. raise 안 함."""
    from src.common import redis_client as rc

    orig_pool = rc._pool
    try:
        fake = AsyncMock()
        fake.set = AsyncMock(return_value=True)  # acquire 성공
        fake.eval = AsyncMock(side_effect=ConnectionError("disconnect"))
        rc._pool = fake  # type: ignore[assignment]

        from src.common.redlock import RedisLock

        lock = RedisLock("test:middisc", ttl_ms=5000)
        got = await lock.__aenter__()
        assert got is True

        # extend 실패 → False. raise 안 함.
        ok = await lock.extend(1000)
        assert ok is False

        # unlock 실패 → silent. raise 안 함.
        await lock.__aexit__(None, None, None)
    finally:
        rc._pool = orig_pool  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# TDD 7: mid-unlock disconnect + 원 예외 보존
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_mid_unlock_disconnect_does_not_raise() -> None:
    """exit 시 Redis 끊겨도 context manager raise 금지 — 기존 예외 전파 유지."""
    from src.common import redis_client as rc

    orig_pool = rc._pool
    try:
        fake = AsyncMock()
        fake.set = AsyncMock(return_value=True)
        fake.eval = AsyncMock(side_effect=ConnectionError("eof"))
        rc._pool = fake  # type: ignore[assignment]

        from src.common.redlock import RedisLock

        lock = RedisLock("test:exitdisc", ttl_ms=1000)

        class _Sentinel(Exception):
            pass

        # 원 예외(_Sentinel)가 unlock 실패로 가려지지 않고 전파되어야 함
        with pytest.raises(_Sentinel):
            async with lock as got:
                assert got is True
                raise _Sentinel("original")
    finally:
        rc._pool = orig_pool  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# TDD 8: Heartbeat extend CAS (TTL 만료 후 타 워커 재획득 → 원 소유자 extend 거부)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_extend_cas_blocks_expired_foreign_acquirer(
    fake_redis: AsyncMock,
) -> None:
    """TTL 만료 → 타 워커 재획득 → 원 소유자의 extend 는 CAS 로 거부."""
    from src.common.redlock import RedisLock

    # first 짧은 TTL 로 획득
    first = RedisLock("test:heartbeat", ttl_ms=50)
    await first.__aenter__()
    assert first.acquired is True

    # TTL 만료 대기
    await asyncio.sleep(0.12)

    # second 가 재획득
    second = RedisLock("test:heartbeat", ttl_ms=5000)
    assert await second.__aenter__() is True

    # first 가 extend 시도 — CAS 로 거부 (token mismatch)
    ok = await first.extend(1000)
    assert ok is False, "CAS extend 는 token 일치 시에만 성공"

    # 정리
    await second.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# TDD 9: Repository wrapping — Redis 장애 → PG fallback 검증
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository_wrapping_redis_unavailable_falls_back_to_pg() -> None:
    """Redis 장애 → PG 단독 실행. acquire_idempotency_lock 이 raise 하지 않음."""
    from src.backtest.repository import BacktestRepository
    from src.common import redis_client as rc

    orig_pool = rc._pool
    try:
        # Redis 장애 simulate
        fake = AsyncMock()
        fake.set = AsyncMock(side_effect=ConnectionError("boom"))
        rc._pool = fake  # type: ignore[assignment]

        # PG session mock — execute 만 검증
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock())

        repo = BacktestRepository(session)
        # raise 하지 않음 (graceful)
        await repo.acquire_idempotency_lock("test-key")

        # PG advisory lock 이 실제로 호출됨
        assert session.execute.await_count == 1
        call_args = session.execute.await_args
        assert "pg_advisory_xact_lock" in str(call_args[0][0])
    finally:
        rc._pool = orig_pool  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# TDD 11: invalid URL graceful degrade (__init__ lazy + __aenter__ try block)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redlock_invalid_url_does_not_raise_in_ctor() -> None:
    """invalid REDIS_LOCK_URL 로 get_redis_lock_pool() 가 ValueError raise 해도
    __init__ 은 폭발 안 하고, __aenter__ 에서 graceful degrade (acquired=False)."""
    from unittest.mock import patch

    from src.common.redlock import RedisLock

    # __init__ 은 절대 raise 안 함
    lock = RedisLock("test:invalid", ttl_ms=1000)
    assert lock.acquired is False

    # __aenter__ 에서 get_redis_lock_pool 가 raise 해도 graceful
    with patch("src.common.redlock.get_redis_lock_pool", side_effect=ValueError("invalid url")):
        got = await lock.__aenter__()
        assert got is False, "invalid URL 은 graceful degrade (PG fallback)"
        assert lock.acquired is False

    # __aexit__ 도 raise 안 함 (acquired=False)
    await lock.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# TDD 10: Redis 정상 환경에서 acquire_idempotency_lock 이 PG 를 방해하지 않음
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository_wrapping_does_not_break_existing_idempotency_flow(
    fake_redis: AsyncMock,
) -> None:
    """Redis 정상 환경에서 acquire_idempotency_lock 이 정상 flow 방해 안 함."""
    from src.backtest.repository import BacktestRepository

    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())

    repo = BacktestRepository(session)
    # Redis 정상 → fast-path 성공. PG 도 호출.
    await repo.acquire_idempotency_lock("integration-key")

    # PG advisory 1회 호출 확인
    assert session.execute.await_count == 1
    call_args = session.execute.await_args
    assert "pg_advisory_xact_lock" in str(call_args[0][0])

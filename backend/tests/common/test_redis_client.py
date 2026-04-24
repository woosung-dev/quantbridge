"""Sprint 10 Phase A1/A2 — Redis lock pool client.

src/common/redis_client.py 의 5 가지 계약:
1. get_redis_lock_pool() singleton 재사용
2. prefork-safe (asyncio.run 다회 호출 안전)
3. healthcheck PING+SET+GET+DEL 정상 → True (Phase A2 upgrade)
4. healthcheck PING+SET+GET+DEL 실패 → False (timeout/connection error 모두)
5. get_redis_lock_pool() ValueError raise 시 흡수 → False
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_redis_lock_pool_returns_same_singleton() -> None:
    """동일 이벤트 루프에서 두 번 호출 시 동일 인스턴스 반환."""
    from src.common.redis_client import get_redis_lock_pool, reset_redis_lock_pool

    reset_redis_lock_pool()  # 다른 테스트의 singleton 격리
    a = get_redis_lock_pool()
    b = get_redis_lock_pool()
    assert a is b


def test_reset_pool_clears_singleton() -> None:
    """Celery prefork worker 재진입 시 singleton 초기화 가능."""
    from src.common.redis_client import (
        get_redis_lock_pool,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()
    a = get_redis_lock_pool()
    reset_redis_lock_pool()
    b = get_redis_lock_pool()
    assert a is not b, "reset 후 신규 인스턴스가 생성되어야 한다"


def test_get_pool_safe_across_event_loops() -> None:
    """asyncio.run 두 번 호출이 첫 번째 루프 종료 후에도 안전.

    Celery prefork worker (`asyncio.run(_execute(...))`) 가 task 마다
    새 이벤트 루프를 만드는 상황을 시뮬레이션.

    NOTE: 본 테스트는 reset 후 신규 instance 생성만 검증. 실제 prefork
    worker FD 복제 시나리오 (부모 process 의 socket FD 가 child 로 복제) 검증은
    Phase A2 integration 테스트에 위임.
    """
    from src.common.redis_client import (
        get_redis_lock_pool,
        reset_redis_lock_pool,
    )

    async def _touch() -> int:
        pool = get_redis_lock_pool()
        return id(pool)

    reset_redis_lock_pool()
    first = asyncio.run(_touch())

    # 새 task 시작 시 자식 프로세스라면 reset 후 진입.
    reset_redis_lock_pool()
    second = asyncio.run(_touch())

    assert first != second  # 다른 instance — close timing 무관 무문제


@pytest.mark.asyncio
async def test_healthcheck_ping_success_sets_healthy_true() -> None:
    """PING+SET+GET+DEL 정상 응답 → app.state.redis_lock_healthy = True (Phase A2 upgrade)."""
    from src.common.redis_client import (
        healthcheck_redis_lock,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()

    fake_pool = AsyncMock()
    fake_pool.ping = AsyncMock(return_value=True)
    fake_pool.set = AsyncMock(return_value=True)
    fake_pool.get = AsyncMock(return_value=b"1")
    fake_pool.delete = AsyncMock(return_value=1)

    fake_app = type("FakeApp", (), {"state": type("State", (), {})()})()

    with patch(
        "src.common.redis_client.get_redis_lock_pool",
        return_value=fake_pool,
    ):
        result = await healthcheck_redis_lock(fake_app)

    assert result is True
    assert fake_app.state.redis_lock_healthy is True
    fake_pool.ping.assert_awaited_once()
    fake_pool.set.assert_awaited_once()
    fake_pool.get.assert_awaited_once()
    fake_pool.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_healthcheck_ping_failure_sets_healthy_false() -> None:
    """PING connection error → degraded 플래그 + 예외 raise 안 함 (Phase A2 upgrade)."""
    from src.common.redis_client import (
        healthcheck_redis_lock,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()

    fake_pool = AsyncMock()
    fake_pool.ping = AsyncMock(side_effect=ConnectionError("boom"))
    # PING 단계에서 이미 실패하므로 set/get/delete 는 호출되지 않음
    fake_pool.set = AsyncMock(return_value=True)
    fake_pool.get = AsyncMock(return_value=b"1")
    fake_pool.delete = AsyncMock(return_value=1)

    fake_app = type("FakeApp", (), {"state": type("State", (), {})()})()

    with patch(
        "src.common.redis_client.get_redis_lock_pool",
        return_value=fake_pool,
    ):
        result = await healthcheck_redis_lock(fake_app)

    assert result is False
    assert fake_app.state.redis_lock_healthy is False


@pytest.mark.asyncio
async def test_healthcheck_absorbs_get_pool_value_error() -> None:
    """get_redis_lock_pool() (Redis.from_url) 가 ValueError raise 해도 흡수.

    invalid REDIS_LOCK_URL (e.g. 잘못된 형식) 시 lifespan startup 이 abort 되지
    않고 degraded 모드로 진입하는지 회귀 방지. M-5 fix 의 핵심 계약.
    """
    from src.common.redis_client import (
        healthcheck_redis_lock,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()

    fake_app = type("FakeApp", (), {"state": type("State", (), {})()})()

    with patch(
        "src.common.redis_client.get_redis_lock_pool",
        side_effect=ValueError("invalid url"),
    ):
        result = await healthcheck_redis_lock(fake_app)

    assert result is False
    assert fake_app.state.redis_lock_healthy is False

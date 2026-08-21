"""Health probe 본문 분기 회귀 테스트.

외부 Postgres·Redis·Celery broker 없이 지연 import 의 원 모듈만 대체하고,
각 probe 함수를 직접 await 해 readiness 의존성 검사를 고정한다.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


class _FakeConnection:
    """Postgres probe의 async connection context manager."""

    def __init__(self) -> None:
        self.execute = AsyncMock()

    async def __aenter__(self) -> _FakeConnection:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class _FakeEngine:
    """연결 또는 연결 전 예외를 제어하는 최소 async engine fake."""

    def __init__(self, connection: _FakeConnection | None = None) -> None:
        self.connect = Mock(return_value=connection)


class _FakeCeleryControl:
    """Celery inspect timeout과 ping 결과를 기록한다."""

    def __init__(self, ping: Mock) -> None:
        self.inspect = Mock(return_value=SimpleNamespace(ping=ping))


def _install_database_engine(
    monkeypatch: pytest.MonkeyPatch,
    engine: object,
) -> None:
    """지연 import되는 database.engine만 테스트 double로 교체한다."""
    import src.common.database as database

    monkeypatch.setattr(database, "engine", engine)


def _install_redis_pool(
    monkeypatch: pytest.MonkeyPatch,
    pool: object,
) -> None:
    """지연 import되는 Redis pool factory만 테스트 double로 교체한다."""
    import src.common.redis_client as redis_client

    monkeypatch.setattr(redis_client, "get_redis_lock_pool", lambda: pool)


def _install_celery_app(
    monkeypatch: pytest.MonkeyPatch,
    celery_app: object,
) -> None:
    """지연 import 경로에 celery_app만 가진 모듈을 주입한다."""
    module = ModuleType("src.tasks.celery_app")
    module.celery_app = celery_app
    monkeypatch.setitem(sys.modules, "src.tasks.celery_app", module)


@pytest.mark.asyncio
async def test_check_postgres_returns_ok_after_select_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정상 probe는 연결 뒤 SELECT 1을 실제 실행한다."""
    from src.health.router import _check_postgres

    connection = _FakeConnection()
    _install_database_engine(monkeypatch, _FakeEngine(connection))

    assert await _check_postgres() == ("ok", None)
    connection.execute.assert_awaited_once()
    assert str(connection.execute.await_args.args[0]) == "SELECT 1"


@pytest.mark.asyncio
async def test_check_postgres_absorbs_connection_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """연결 예외는 밖으로 전파하지 않고 실패 메시지로 반환한다."""
    from src.health.router import _check_postgres

    error = RuntimeError("postgres unavailable")
    engine = _FakeEngine()
    engine.connect.side_effect = error
    _install_database_engine(monkeypatch, engine)

    assert await _check_postgres() == ("fail", "postgres unavailable")


@pytest.mark.asyncio
async def test_check_postgres_reports_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """타임아웃 실패 메시지는 Postgres timeout 상수를 포함한다."""
    from src.health.router import _PG_TIMEOUT_S, _check_postgres

    engine = _FakeEngine()
    engine.connect.side_effect = TimeoutError
    _install_database_engine(monkeypatch, engine)

    assert await _check_postgres() == ("fail", f"timeout after {_PG_TIMEOUT_S}s")


@pytest.mark.asyncio
async def test_check_redis_returns_fail_when_ping_is_falsy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis PING False는 예외 없이 readiness 실패다."""
    from src.health.router import _check_redis

    pool = SimpleNamespace(ping=AsyncMock(return_value=False))
    _install_redis_pool(monkeypatch, pool)

    assert await _check_redis() == ("fail", "PING returned False")
    pool.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_redis_returns_ok_when_ping_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis PING True는 정상 결과를 반환한다."""
    from src.health.router import _check_redis

    pool = SimpleNamespace(ping=AsyncMock(return_value=True))
    _install_redis_pool(monkeypatch, pool)

    assert await _check_redis() == ("ok", None)
    pool.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_redis_absorbs_ping_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis PING 예외는 실패 메시지로 흡수한다."""
    from src.health.router import _check_redis

    pool = SimpleNamespace(ping=AsyncMock(side_effect=RuntimeError("redis down")))
    _install_redis_pool(monkeypatch, pool)

    assert await _check_redis() == ("fail", "redis down")


@pytest.mark.asyncio
async def test_check_redis_reports_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis timeout은 timeout 상수를 포함한 실패로 반환한다."""
    from src.health.router import _REDIS_TIMEOUT_S, _check_redis

    pool = SimpleNamespace(ping=AsyncMock(side_effect=TimeoutError))
    _install_redis_pool(monkeypatch, pool)

    assert await _check_redis() == ("fail", f"timeout after {_REDIS_TIMEOUT_S}s")


@pytest.mark.asyncio
async def test_check_celery_workers_reports_module_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sys.modules None sentinel으로 지연 celery import 실패를 재현한다."""
    from src.health.router import _check_celery_workers

    monkeypatch.setitem(sys.modules, "src.tasks.celery_app", None)

    worker_count, error = await _check_celery_workers()

    assert worker_count == 0
    assert error is not None
    assert error.startswith("celery_app import failed: ")
    assert "src.tasks.celery_app" in error


@pytest.mark.asyncio
@pytest.mark.parametrize("result", [None, {}], ids=["none", "empty-dict"])
async def test_check_celery_workers_reports_no_response_for_falsy_ping(
    monkeypatch: pytest.MonkeyPatch,
    result: dict[object, object] | None,
) -> None:
    """None과 빈 dict ping 결과는 모두 worker 0으로 처리한다."""
    from src.health.router import _check_celery_workers

    control = _FakeCeleryControl(Mock(return_value=result))
    _install_celery_app(monkeypatch, SimpleNamespace(control=control))

    assert await _check_celery_workers() == (0, "no workers responded")


@pytest.mark.asyncio
async def test_check_celery_workers_counts_each_worker_and_passes_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """inspect에는 env timeout을 전달하고 ping 응답 dict의 worker 수를 센다."""
    from src.health.router import _check_celery_workers

    monkeypatch.setenv("HEALTHZ_CELERY_TIMEOUT_S", "7.25")
    control = _FakeCeleryControl(
        Mock(return_value={"worker-a": {"ok": "pong"}, "worker-b": {"ok": "pong"}})
    )
    _install_celery_app(monkeypatch, SimpleNamespace(control=control))

    assert await _check_celery_workers() == (2, None)
    control.inspect.assert_called_once_with(timeout=7.25)


@pytest.mark.asyncio
async def test_check_celery_workers_reports_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Celery inspect timeout은 설정된 timeout 값을 포함해 실패한다."""
    from src.health.router import _check_celery_workers

    monkeypatch.setenv("HEALTHZ_CELERY_TIMEOUT_S", "6.5")
    control = _FakeCeleryControl(Mock(side_effect=TimeoutError))
    _install_celery_app(monkeypatch, SimpleNamespace(control=control))

    assert await _check_celery_workers() == (0, "timeout after 6.5s")


@pytest.mark.asyncio
async def test_check_celery_workers_absorbs_inspect_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Celery inspect 일반 예외는 메시지를 보존한 실패로 반환한다."""
    from src.health.router import _check_celery_workers

    control = _FakeCeleryControl(Mock(side_effect=RuntimeError("broker refused")))
    _install_celery_app(monkeypatch, SimpleNamespace(control=control))

    assert await _check_celery_workers() == (0, "broker refused")


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [(None, 12.0), ("9.75", 9.75), ("not-a-number", 12.0)],
    ids=["default", "override", "invalid-fallback"],
)
def test_get_celery_timeout_s_uses_env_or_default(
    monkeypatch: pytest.MonkeyPatch,
    env_value: str | None,
    expected: float,
) -> None:
    """Celery timeout은 미설정·유효값·파싱 불가값 모두를 고정한다."""
    from src.health.router import _get_celery_timeout_s

    if env_value is None:
        monkeypatch.delenv("HEALTHZ_CELERY_TIMEOUT_S", raising=False)
    else:
        monkeypatch.setenv("HEALTHZ_CELERY_TIMEOUT_S", env_value)

    assert _get_celery_timeout_s() == expected

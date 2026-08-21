"""Alembic advisory-lock entrypoint의 외부 경계와 종료 계약을 고정한다."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import asyncpg
import pytest

from src.scripts import run_alembic_with_lock as alembic_lock


class _FakeConnection:
    """lock 시도 결과와 close 호출을 기록하는 asyncpg connection fake."""

    def __init__(self, outcomes: list[bool], *, close_error: Exception | None = None) -> None:
        self._outcomes = iter(outcomes)
        self.close_calls = 0
        self.close_error = close_error
        self.fetchval_calls: list[tuple[str, int]] = []

    async def fetchval(self, query: str, lock_key: int) -> bool:
        self.fetchval_calls.append((query, lock_key))
        return next(self._outcomes)

    async def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class _FakeClock:
    """sleep마다 진행되는 loop clock fake."""

    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now


class _FakeProcess:
    """wait 반환값과 호출 횟수를 기록하는 subprocess fake."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.wait_calls = 0

    async def wait(self) -> int:
        self.wait_calls += 1
        return self.returncode


def _set_database_url(monkeypatch: pytest.MonkeyPatch, database_url: str | None) -> None:
    """run()이 지연 import하는 설정 객체를 테스트 값으로 교체한다."""
    from src.core import config

    monkeypatch.setattr(config, "settings", SimpleNamespace(database_url=database_url))


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgresql+asyncpg://user:password@db/quantbridge",
            "postgresql://user:password@db/quantbridge",
        ),
        ("postgresql://user:password@db/quantbridge", "postgresql://user:password@db/quantbridge"),
        ("postgres://user:password@db/quantbridge", "postgres://user:password@db/quantbridge"),
        (
            "postgresql+asyncpg://db/postgresql+asyncpg://preserved",
            "postgresql://db/postgresql+asyncpg://preserved",
        ),
    ],
)
def test_normalize_url_for_asyncpg_preserves_non_leading_prefixes(
    database_url: str, expected: str
) -> None:
    """asyncpg dialect만 첫 접두사에서 제거하고 나머지 URL 문자는 보존한다."""
    assert alembic_lock._normalize_url_for_asyncpg(database_url) == expected


def test_parse_args_uses_documented_defaults() -> None:
    """인자 생략 시 운영 entrypoint의 고정 lock·timeout 기본값을 쓴다."""
    args = alembic_lock._parse_args([])

    assert args.lock_key == 1903723824
    assert args.timeout == 30


def test_parse_args_uses_explicit_values() -> None:
    """CLI 명시값은 변환 없이 lock 획득 함수까지 전달할 정수로 남는다."""
    args = alembic_lock._parse_args(["--lock-key", "7", "--timeout", "3"])

    assert args.lock_key == 7
    assert args.timeout == 3


@pytest.mark.asyncio
async def test_acquire_advisory_lock_returns_open_connection_on_first_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 lock 획득은 대기·close 없이 같은 connection을 호출자에게 넘긴다."""
    conn = _FakeConnection([True])
    connect = AsyncMock(return_value=conn)
    sleep = AsyncMock()
    monkeypatch.setattr(asyncpg, "connect", connect)
    monkeypatch.setattr(alembic_lock.asyncio, "sleep", sleep)

    result = await alembic_lock._acquire_advisory_lock(
        "postgresql+asyncpg://user:password@db/quantbridge", 7, 30
    )

    assert result is conn
    assert conn.close_calls == 0
    connect.assert_awaited_once_with("postgresql://user:password@db/quantbridge")
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_acquire_advisory_lock_retries_once_before_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 경합 실패 뒤 1초 대기하고 두 번째 시도에서 열린 connection을 반환한다."""
    clock = _FakeClock()
    conn = _FakeConnection([False, True])
    sleep_calls: list[float] = []

    async def _sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(asyncpg, "connect", AsyncMock(return_value=conn))
    monkeypatch.setattr(alembic_lock.asyncio, "get_event_loop", lambda: clock)
    monkeypatch.setattr(alembic_lock.asyncio, "sleep", _sleep)

    result = await alembic_lock._acquire_advisory_lock("postgresql://db/quantbridge", 7, 30)

    assert result is conn
    assert len(conn.fetchval_calls) == 2
    assert sleep_calls == [1.0]
    assert conn.close_calls == 0


@pytest.mark.asyncio
async def test_acquire_advisory_lock_closes_connection_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """timeout 소진 경로는 RuntimeError 전파 전에 연결을 닫아 누수를 막는다."""
    clock = _FakeClock()
    conn = _FakeConnection([False, False])

    async def _sleep(seconds: float) -> None:
        clock.now += seconds

    monkeypatch.setattr(asyncpg, "connect", AsyncMock(return_value=conn))
    monkeypatch.setattr(alembic_lock.asyncio, "get_event_loop", lambda: clock)
    monkeypatch.setattr(alembic_lock.asyncio, "sleep", _sleep)

    with pytest.raises(RuntimeError, match="not acquired within 1s"):
        await alembic_lock._acquire_advisory_lock("postgresql://db/quantbridge", 7, 1)

    assert conn.close_calls == 1


@pytest.mark.asyncio
async def test_acquire_advisory_lock_with_zero_timeout_fails_without_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """관측 계약: timeout=0은 첫 실패 직후 대기 없이 RuntimeError가 된다."""
    conn = _FakeConnection([False])
    sleep = AsyncMock()
    monkeypatch.setattr(asyncpg, "connect", AsyncMock(return_value=conn))
    monkeypatch.setattr(alembic_lock.asyncio, "sleep", sleep)

    with pytest.raises(RuntimeError, match="not acquired within 0s"):
        await alembic_lock._acquire_advisory_lock("postgresql://db/quantbridge", 7, 0)

    assert conn.close_calls == 1
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_alembic_upgrade_head_uses_exact_argv_and_returns_wait_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """운영 subprocess의 실행 순서와 wait 반환값 전달을 통째로 고정한다."""
    proc = _FakeProcess(returncode=3)
    create_subprocess = AsyncMock(return_value=proc)
    monkeypatch.setattr(alembic_lock.asyncio, "create_subprocess_exec", create_subprocess)

    result = await alembic_lock._run_alembic_upgrade_head()

    assert result == 3
    assert proc.wait_calls == 1
    create_subprocess.assert_awaited_once_with("uv", "run", "alembic", "upgrade", "head")


@pytest.mark.asyncio
async def test_run_returns_upgrade_code_when_connection_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """lock release 실패는 이미 끝난 alembic 결과를 바꾸지 않는다."""
    conn = _FakeConnection([True], close_error=RuntimeError("close failed"))
    acquire = AsyncMock(return_value=conn)
    upgrade = AsyncMock(return_value=3)
    _set_database_url(monkeypatch, "postgresql://db/quantbridge")
    monkeypatch.setattr(alembic_lock, "_acquire_advisory_lock", acquire)
    monkeypatch.setattr(alembic_lock, "_run_alembic_upgrade_head", upgrade)

    result = await alembic_lock.run(7, 30)

    assert result == 3
    assert conn.close_calls == 1
    acquire.assert_awaited_once_with("postgresql://db/quantbridge", 7, 30)
    upgrade.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_closes_connection_when_upgrade_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """alembic 실패도 finally를 거쳐 lock connection을 해제한다."""
    conn = _FakeConnection([True])
    _set_database_url(monkeypatch, "postgresql://db/quantbridge")
    monkeypatch.setattr(alembic_lock, "_acquire_advisory_lock", AsyncMock(return_value=conn))
    monkeypatch.setattr(
        alembic_lock,
        "_run_alembic_upgrade_head",
        AsyncMock(side_effect=RuntimeError("upgrade failed")),
    )

    with pytest.raises(RuntimeError, match="upgrade failed"):
        await alembic_lock.run(7, 30)

    assert conn.close_calls == 1


def test_main_maps_runtime_error_to_exit_code_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """lock 경합 timeout은 entrypoint 관점에서 rc 2로 변환한다."""
    monkeypatch.setattr(alembic_lock, "run", AsyncMock(side_effect=RuntimeError("timeout")))

    assert alembic_lock.main([]) == 2


def test_main_returns_nonzero_subprocess_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 wrapper 경로는 alembic의 0이 아닌 종료 코드도 보존한다."""
    monkeypatch.setattr(alembic_lock, "run", AsyncMock(return_value=3))

    assert alembic_lock.main([]) == 3


@pytest.mark.asyncio
async def test_run_rejects_missing_database_url_before_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DATABASE_URL 미설정은 asyncpg 연결 전 명시적인 RuntimeError로 끝난다."""
    connect = AsyncMock()
    _set_database_url(monkeypatch, None)
    monkeypatch.setattr(asyncpg, "connect", connect)

    with pytest.raises(RuntimeError, match="DATABASE_URL not configured"):
        await alembic_lock.run(7, 30)

    connect.assert_not_awaited()

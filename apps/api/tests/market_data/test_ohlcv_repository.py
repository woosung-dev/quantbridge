"""OHLCVRepository — TimescaleDB ts.ohlcv 접근 테스트."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.market_data.repository import OHLCVRepository


def _bar(time: datetime, **overrides: object) -> dict[str, object]:
    """OHLCV row dict 헬퍼 — 기본값 BTC/USDT 1h bybit."""
    base: dict[str, object] = {
        "time": time,
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "exchange": "bybit",
        "open": Decimal("40000.0"),
        "high": Decimal("41000.0"),
        "low": Decimal("39000.0"),
        "close": Decimal("40500.0"),
        "volume": Decimal("100.0"),
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_insert_bulk_and_get_range(db_session: AsyncSession) -> None:
    """insert_bulk → get_range 라운드트립."""
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [_bar(base + timedelta(hours=i)) for i in range(5)]

    await repo.insert_bulk(rows)
    await repo.commit()

    fetched = await repo.get_range(
        "BTC/USDT", "1h", base, base + timedelta(hours=4)
    )
    assert len(fetched) == 5
    assert fetched[0].time == base
    assert fetched[-1].time == base + timedelta(hours=4)
    # ASC 정렬 검증
    assert all(
        fetched[i].time < fetched[i + 1].time for i in range(len(fetched) - 1)
    )


@pytest.mark.asyncio
async def test_insert_bulk_on_conflict_do_nothing(db_session: AsyncSession) -> None:
    """동일 PK row 중복 insert 시 silently skip."""
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    row = _bar(base, open=Decimal("40000"), high=Decimal("40000"))

    await repo.insert_bulk([row])
    await repo.commit()
    # 두 번째 insert — 동일 PK, ON CONFLICT DO NOTHING으로 무시
    await repo.insert_bulk([row])
    await repo.commit()

    fetched = await repo.get_range(
        "BTC/USDT", "1h", base, base + timedelta(hours=1)
    )
    assert len(fetched) == 1


@pytest.mark.asyncio
async def test_insert_bulk_empty_noop(db_session: AsyncSession) -> None:
    """빈 list insert는 no-op (예외 없음)."""
    repo = OHLCVRepository(db_session)
    await repo.insert_bulk([])
    await repo.commit()


@pytest.mark.asyncio
async def test_find_gaps_full_missing(db_session: AsyncSession) -> None:
    """전체 구간 누락 → 단일 gap."""
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    gaps = await repo.find_gaps(
        "BTC/USDT", "1h", base, base + timedelta(hours=4), 3600
    )
    # 5 timestamps (0, 1h, 2h, 3h, 4h) 모두 누락 → 인접 grouping으로 1개 gap
    assert len(gaps) == 1
    assert gaps[0][0] == base
    assert gaps[0][1] == base + timedelta(hours=4)


@pytest.mark.asyncio
async def test_find_gaps_no_gap_when_complete(db_session: AsyncSession) -> None:
    """전체 구간 채워져 있으면 gap 없음."""
    repo = OHLCVRepository(db_session)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [_bar(base + timedelta(hours=i)) for i in range(5)]
    await repo.insert_bulk(rows)
    await repo.commit()

    gaps = await repo.find_gaps(
        "BTC/USDT", "1h", base, base + timedelta(hours=4), 3600
    )
    assert gaps == []


def _lock_key(symbol: str, tf: str, start: datetime, end: datetime) -> str:
    """acquire_fetch_lock이 사용하는 key 포맷과 일치해야 함."""
    return f"ohlcv:{symbol}:{tf}:{start.isoformat()}:{end.isoformat()}"


@pytest.mark.asyncio
async def test_acquire_fetch_lock_exclusion(_test_engine: AsyncEngine) -> None:
    """acquire_fetch_lock이 mutual exclusion을 제공하는지 결정적으로 검증.

    Timing gather 대신 pg_try_advisory_xact_lock으로 non-blocking probe.
    - holder session이 lock 보유 중 → probe는 False
    - holder commit 후 → 새 session이 즉시 acquire 가능

    실제 M3 사용 패턴(Service → Repository.commit)과 동일한 session flow.
    """
    base = datetime(2024, 1, 1, tzinfo=UTC)
    period_end = base + timedelta(hours=1)
    symbol, timeframe = "BTC/USDT", "1h"
    key_str = _lock_key(symbol, timeframe, base, period_end)

    session_maker = async_sessionmaker(_test_engine, expire_on_commit=False)

    # 1. holder session이 lock 획득 (commit 하지 않고 보유 유지)
    holder = session_maker()
    holder_repo = OHLCVRepository(holder)
    await holder_repo.acquire_fetch_lock(symbol, timeframe, base, period_end)

    try:
        # 2. probe session이 same key로 try-lock → False여야 함 (holder가 보유 중)
        async with session_maker() as probe:
            result = await probe.execute(
                text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
                {"key": key_str},
            )
            acquired = result.scalar()
            assert acquired is False, (
                "holder가 advisory lock을 보유 중인데 probe가 try-acquire에 "
                "성공함 — lock이 실제로 걸리지 않음"
            )
    finally:
        # 3. holder commit → lock 해제
        await holder_repo.commit()
        await holder.close()

    # 4. 해제 후 새 session이 즉시 acquire 가능해야 함
    async with session_maker() as after:
        after_repo = OHLCVRepository(after)
        await after_repo.acquire_fetch_lock(symbol, timeframe, base, period_end)
        await after_repo.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("previous_timeout", ["0", "250ms", "45s"])
async def test_acquire_fetch_lock_bounds_wait_and_restores_previous_timeout(
    previous_timeout: str,
) -> None:
    """획득에만 10초 제한을 쓰고 이후 SQL에는 원래 timeout을 보존한다."""
    from unittest.mock import AsyncMock, Mock

    session = AsyncMock(spec=AsyncSession)
    previous_result = Mock()
    previous_result.scalar_one.return_value = previous_timeout
    session.execute.side_effect = [previous_result, None, None, None]
    base = datetime(2024, 1, 1, tzinfo=UTC)
    end = base + timedelta(hours=1)

    await OHLCVRepository(session).acquire_fetch_lock("BTC/USDT:USDT", "1h", base, end)

    calls = session.execute.await_args_list
    assert [str(call.args[0]) for call in calls] == [
        "SELECT current_setting('lock_timeout')",
        "SET LOCAL lock_timeout = '10s'",
        "SELECT pg_advisory_xact_lock(hashtext(:key))",
        "SELECT set_config('lock_timeout', :previous_timeout, true)",
    ]
    assert calls[2].args[1] == {"key": _lock_key("BTC/USDT:USDT", "1h", base, end)}
    assert calls[3].args[1] == {"previous_timeout": previous_timeout}
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_stage", ["read_setting", "set_local", "lock", "restore_setting"])
async def test_acquire_fetch_lock_rolls_back_before_propagating_db_error(
    failure_stage: str,
) -> None:
    """설정 조회·적용·복원/락 SQL 실패는 rollback 후 같은 예외를 전파한다."""
    from unittest.mock import AsyncMock, Mock

    from sqlalchemy.exc import OperationalError

    session = AsyncMock(spec=AsyncSession)
    error = OperationalError("lock wait", {}, RuntimeError("lock timeout"))
    previous_result = Mock()
    previous_result.scalar_one.return_value = "250ms"
    failure_index = ["read_setting", "set_local", "lock", "restore_setting"].index(failure_stage)
    session.execute.side_effect = [*[previous_result, None, None][:failure_index], error]
    base = datetime(2024, 1, 1, tzinfo=UTC)

    with pytest.raises(OperationalError) as caught:
        await OHLCVRepository(session).acquire_fetch_lock("BTC/USDT", "1h", base, base)

    assert caught.value is error
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()
    assert session.execute.await_count == failure_index + 1


@pytest.mark.asyncio
async def test_acquire_fetch_lock_does_not_handle_non_database_error() -> None:
    """일반 예외를 DB 거래 실패로 간주해 rollback하지 않는다."""
    from unittest.mock import AsyncMock

    session = AsyncMock(spec=AsyncSession)
    error = RuntimeError("fixture operation failed")
    session.execute.side_effect = error
    base = datetime(2024, 1, 1, tzinfo=UTC)

    with pytest.raises(RuntimeError) as caught:
        await OHLCVRepository(session).acquire_fetch_lock("BTC/USDT", "1h", base, base)

    assert caught.value is error
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()

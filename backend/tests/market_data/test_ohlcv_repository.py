"""OHLCVRepository — TimescaleDB ts.ohlcv 접근 테스트."""
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
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


@pytest.mark.asyncio
async def test_acquire_fetch_lock_blocks_concurrent_call(
    _test_engine: AsyncEngine,
) -> None:
    """첫 번째 lock holder가 트랜잭션을 commit/rollback할 때까지 두 번째는 대기.

    db_session(savepoint 격리) 우회 — advisory lock은 실제 outer transaction
    boundary에서만 해제되므로 별도 connection + 별도 transaction 필요.
    """
    base = datetime(2024, 1, 1, tzinfo=UTC)
    completed_order: list[str] = []

    async def first_lock_holder() -> None:
        async with _test_engine.connect() as conn:
            tx = await conn.begin()
            session = async_sessionmaker(bind=conn, expire_on_commit=False)()
            repo = OHLCVRepository(session)
            await repo.acquire_fetch_lock(
                "BTC/USDT", "1h", base, base + timedelta(hours=1)
            )
            completed_order.append("first_acquired")
            await asyncio.sleep(0.5)  # hold the lock
            await tx.commit()
            completed_order.append("first_released")
            await session.close()

    async def second_lock_holder() -> None:
        # first_lock_holder가 먼저 획득하도록 보장
        await asyncio.sleep(0.1)
        async with _test_engine.connect() as conn:
            tx = await conn.begin()
            session = async_sessionmaker(bind=conn, expire_on_commit=False)()
            repo = OHLCVRepository(session)
            await repo.acquire_fetch_lock(
                "BTC/USDT", "1h", base, base + timedelta(hours=1)
            )
            completed_order.append("second_acquired")
            await tx.commit()
            await session.close()

    await asyncio.gather(first_lock_holder(), second_lock_holder())

    # 핵심: second_acquired는 반드시 first_released 이후
    assert completed_order == [
        "first_acquired",
        "first_released",
        "second_acquired",
    ]

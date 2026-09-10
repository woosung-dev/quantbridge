"""TimescaleProvider — cache → CCXT fallback + advisory lock 테스트.

★BL-535 — 인자는 canonical 시장(`BTC/USDT`)이지만 **저장 키는 상품**(`BTC/USDT:USDT`)이다.
그래서 픽스처도 상품 키로 심는다. 그 경계 자체의 회귀는
`test_backtest_instrument_parity.py` 가 잠근다.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from src.market_data.models import OHLCV
from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.repository import OHLCVRepository


def _orm_row(ts: datetime) -> OHLCV:
    """`_to_dataframe` 입력용 OHLCV 인스턴스 — DB 에 넣지 않는다(순수 변환 테스트)."""
    return OHLCV(
        time=ts,
        symbol="BTC/USDT:USDT",
        timeframe="1h",
        exchange="bybit",
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
    )


def _db_row(base: datetime, offset_h: int) -> dict[str, object]:
    return {
        "time": base + timedelta(hours=offset_h),
        "symbol": "BTC/USDT:USDT",
        "timeframe": "1h",
        "exchange": "bybit",
        "open": Decimal("1"),
        "high": Decimal("1"),
        "low": Decimal("1"),
        "close": Decimal("1"),
        "volume": Decimal("1"),
    }


@pytest.mark.asyncio
async def test_get_ohlcv_full_cache_hit_no_ccxt_call(db_session) -> None:
    """모든 구간이 cache에 있으면 CCXT 호출 0회."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    rows = [_db_row(base, i) for i in range(5)]
    await repo.insert_bulk(rows)
    await repo.commit()

    mock_ccxt = AsyncMock(spec=CCXTProvider)
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")
    df = await provider.get_ohlcv("BTC/USDT", "1h", base, base + timedelta(hours=4))

    assert len(df) == 5
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    mock_ccxt.fetch_ohlcv.assert_not_called()


@pytest.mark.asyncio
async def test_get_ohlcv_partial_cache_fetches_gaps(db_session) -> None:
    """부분 cache → gap만 CCXT fetch 후 insert."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    # bars 0,1,2 있음 — bars 3,4 없음 (gap)
    await repo.insert_bulk([_db_row(base, i) for i in range(3)])
    await repo.commit()

    mock_ccxt = AsyncMock(spec=CCXTProvider)
    base_ms = int((base + timedelta(hours=3)).timestamp() * 1000)
    mock_ccxt.fetch_ohlcv.return_value = [
        [base_ms + i * 3_600_000, 1.0, 1.0, 1.0, 1.0, 1.0] for i in range(2)
    ]
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    df = await provider.get_ohlcv("BTC/USDT", "1h", base, base + timedelta(hours=4))
    assert len(df) == 5  # cache 3 + fetched 2
    mock_ccxt.fetch_ohlcv.assert_called_once()


@pytest.mark.asyncio
async def test_get_ohlcv_empty_when_no_cache_no_ccxt_response(db_session) -> None:
    """cache도 없고 CCXT도 빈 응답 → 빈 DataFrame (error 없음)."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    mock_ccxt = AsyncMock(spec=CCXTProvider)
    mock_ccxt.fetch_ohlcv.return_value = []
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    df = await provider.get_ohlcv("BTC/USDT", "1h", base, base + timedelta(hours=4))
    assert len(df) == 0
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


@pytest.mark.asyncio
async def test_get_ohlcv_normalizes_symbol(db_session) -> None:
    """'BTCUSDT' concat 입력도 상품 키 'BTC/USDT:USDT' 로 해석되어 조회된다."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    # 저장 키(상품 표기)로 pre-insert
    await repo.insert_bulk([_db_row(base, 0)])
    await repo.commit()

    mock_ccxt = AsyncMock(spec=CCXTProvider)
    mock_ccxt.fetch_ohlcv.return_value = []
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    df = await provider.get_ohlcv("BTCUSDT", "1h", base, base + timedelta(hours=0))
    assert len(df) == 1


# ── [BL-842] ⑶ 빈 결과의 index 타입 ──────────────────────────────────────────
# ★위의 `test_get_ohlcv_empty_when_no_cache_no_ccxt_response` 는 `len(df) == 0` 과
#   columns 만 잰다 — **index 타입은 아무도 안 재고 있었다.** 종전 구현은 빈 경우에만
#   RangeIndex 를 내서, 같은 무-데이터 입력이 채워진 경우(DatetimeIndex)와 다른 모양이
#   됐다. 아래 둘은 DB 를 타지 않는다(`_to_dataframe` 는 staticmethod).


def test_empty_dataframe_has_datetime_index() -> None:
    """빈 결과도 DatetimeIndex 다 — RangeIndex 면 red."""
    df = TimescaleProvider._to_dataframe([])

    assert len(df) == 0
    assert isinstance(df.index, pd.DatetimeIndex), (
        f"빈 결과의 index 가 {type(df.index).__name__} 다 — 채워진 경우와 모양이 다르면 "
        "소비자가 index 타입으로 분기할 때 침묵 실패한다 ([BL-842] ⑶)"
    )
    assert df.index.name == "time"
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_empty_and_filled_dataframes_share_index_type() -> None:
    """빈 경우와 채워진 경우의 index 타입·tz·이름이 같다."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    filled = TimescaleProvider._to_dataframe([_orm_row(base)])
    empty = TimescaleProvider._to_dataframe([])

    assert type(empty.index) is type(filled.index)
    assert empty.index.name == filled.index.name
    assert empty.index.tz == filled.index.tz


@pytest.mark.asyncio
async def test_cache_hit_releases_fetch_transaction_before_return():
    """갭이 없어도 optimizer 계산 전에 락이 해제되어야 한다."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = AsyncMock(spec=OHLCVRepository)
    repo.find_gaps.return_value = []
    repo.get_range.return_value = [_orm_row(base)]
    provider = TimescaleProvider(repo, AsyncMock(spec=CCXTProvider))
    await provider.get_ohlcv("BTC/USDT", "1h", base, base)
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_failure_rolls_back_before_propagating():
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = AsyncMock(spec=OHLCVRepository)
    repo.find_gaps.return_value = [(base, base)]
    ccxt = AsyncMock(spec=CCXTProvider)
    ccxt.fetch_ohlcv.side_effect = TimeoutError("exchange timeout")
    with pytest.raises(TimeoutError):
        await TimescaleProvider(repo, ccxt).get_ohlcv("BTC/USDT", "1h", base, base)
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_lock_is_bounded_and_failed_transaction_is_reusable(_test_engine):
    """별도 연결이 락을 보유해도 5초 후 실패하고 다음 SQL은 실행 가능하다."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import AsyncSession

    base = datetime(2024, 1, 1, tzinfo=UTC)
    async with AsyncSession(_test_engine) as holder, AsyncSession(_test_engine) as waiter:
        holder_repo = OHLCVRepository(holder)
        await holder_repo.acquire_fetch_lock("BTC/USDT:USDT", "1h", base, base)
        ccxt = AsyncMock(spec=CCXTProvider)
        provider = TimescaleProvider(OHLCVRepository(waiter), ccxt)
        try:
            with pytest.raises(DBAPIError, match="lock timeout"):
                await asyncio.wait_for(provider.get_ohlcv("BTC/USDT", "1h", base, base), timeout=10)
            assert await waiter.scalar(text("SELECT 1")) == 1
            ccxt.fetch_ohlcv.assert_not_awaited()
        finally:
            await holder.rollback()


@pytest.mark.asyncio
async def test_fetch_releases_lock_for_another_connection(_test_engine):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    base = datetime(2024, 1, 1, tzinfo=UTC)
    async with (
        _test_engine.connect() as connection,
        AsyncSession(connection) as first,
        AsyncSession(_test_engine) as second,
    ):
        await first.execute(text("SET lock_timeout = '2s'"))
        ccxt = AsyncMock(spec=CCXTProvider)
        ccxt.fetch_ohlcv.return_value = []
        await TimescaleProvider(OHLCVRepository(first), ccxt).get_ohlcv(
            "BTC/USDT", "1h", base, base
        )
        assert await first.scalar(text("SHOW lock_timeout")) == "2s"
        key = f"ohlcv:BTC/USDT:USDT:1h:{base.isoformat()}:{base.isoformat()}"
        assert (
            await second.scalar(
                text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"), {"key": key}
            )
            is True
        )

"""TimescaleProvider — cache → CCXT fallback + advisory lock 테스트."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.repository import OHLCVRepository


def _db_row(base: datetime, offset_h: int) -> dict[str, object]:
    return {
        "time": base + timedelta(hours=offset_h),
        "symbol": "BTC/USDT",
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
    df = await provider.get_ohlcv(
        "BTC/USDT", "1h", base, base + timedelta(hours=4)
    )

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

    df = await provider.get_ohlcv(
        "BTC/USDT", "1h", base, base + timedelta(hours=4)
    )
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

    df = await provider.get_ohlcv(
        "BTC/USDT", "1h", base, base + timedelta(hours=4)
    )
    assert len(df) == 0
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


@pytest.mark.asyncio
async def test_get_ohlcv_normalizes_symbol(db_session) -> None:
    """'BTCUSDT' 입력을 'BTC/USDT'로 정규화하여 조회."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    repo = OHLCVRepository(db_session)
    # 정규화된 symbol로 pre-insert
    await repo.insert_bulk([_db_row(base, 0)])
    await repo.commit()

    mock_ccxt = AsyncMock(spec=CCXTProvider)
    mock_ccxt.fetch_ohlcv.return_value = []
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    df = await provider.get_ohlcv(
        "BTCUSDT", "1h", base, base + timedelta(hours=0)
    )
    assert len(df) == 1

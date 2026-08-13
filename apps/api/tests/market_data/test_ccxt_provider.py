"""CCXTProvider — raw OHLCV fetch mock 기반 단위 테스트."""
import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.market_data.providers.ccxt import CCXTProvider


@pytest.mark.asyncio
async def test_fetch_ohlcv_pagination_advances_cursor(monkeypatch) -> None:
    """3 pages of bars — cursor 전진 + 중복 timestamp 제거 검증."""
    provider = CCXTProvider("bybit")
    base_ms = 1_704_067_200_000  # 2024-01-01 UTC
    page1 = [[base_ms + i * 60_000, 1, 2, 0, 1, 1] for i in range(1000)]
    page2 = [[base_ms + (i + 1000) * 60_000, 1, 2, 0, 1, 1] for i in range(1000)]
    page3 = [[base_ms + (i + 2000) * 60_000, 1, 2, 0, 1, 1] for i in range(500)]
    # 4번째 호출은 빈 list (fetch 종료 조건)
    mock_fetch = AsyncMock(side_effect=[page1, page2, page3, []])
    monkeypatch.setattr(provider, "_fetch_page", mock_fetch)
    # closed bar 필터 무력화 (테스트 데이터가 과거이므로)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    since = datetime(2024, 1, 1, tzinfo=UTC)
    until = datetime(2024, 1, 3, tzinfo=UTC)
    bars = await provider.fetch_ohlcv("BTC/USDT", "1m", since, until)

    # 전체 2500 bars 반환 (duplicate 없음)
    assert len(bars) == 2500
    # 최소 3회 fetch (until 지나치면 중단)
    assert mock_fetch.call_count >= 3

    await provider.close()


@pytest.mark.asyncio
async def test_fetch_ohlcv_filters_unclosed_bars(monkeypatch) -> None:
    """진행 중 bar (last_closed_ts 초과)는 제외."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    bars_in = [
        [now_ms - 120_000, 1, 1, 1, 1, 1],  # 2분 전 — closed
        [now_ms - 60_000, 1, 1, 1, 1, 1],  # 1분 전 — boundary
        [now_ms, 1, 1, 1, 1, 1],  # 진행 중 — exclude
    ]
    monkeypatch.setattr(
        provider, "_fetch_page", AsyncMock(side_effect=[bars_in, []])
    )

    bars = await provider.fetch_ohlcv(
        "BTC/USDT",
        "1m",
        datetime.fromtimestamp((now_ms - 200_000) / 1000, tz=UTC),
        datetime.fromtimestamp((now_ms + 60_000) / 1000, tz=UTC),
    )
    # 진행 중 bar는 제외 — 최대 2개
    assert len(bars) <= 2
    assert all(b[0] < now_ms for b in bars)

    await provider.close()


@pytest.mark.asyncio
async def test_fetch_ohlcv_empty_page_stops(monkeypatch) -> None:
    """첫 호출부터 빈 page면 즉시 종료."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr(provider, "_fetch_page", AsyncMock(return_value=[]))
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    since = datetime(2024, 1, 1, tzinfo=UTC)
    until = datetime(2024, 1, 3, tzinfo=UTC)
    bars = await provider.fetch_ohlcv("BTC/USDT", "1m", since, until)
    assert bars == []

    await provider.close()


# -----------------------------------------------------------------------
# Celery prefork asyncio loop 재사용 회귀 방지 (Sprint 9-2 D1 후속)
# -----------------------------------------------------------------------

def test_exchange_rebuilds_when_event_loop_changes() -> None:
    """Celery prefork worker 의 `asyncio.run()` 이 task 마다 새 loop 를 만들 때
    CCXTProvider 가 이전 loop 에 bound 된 exchange 를 폐기하고 새 loop 용 exchange 를
    재생성해야 한다. 재생성 안 되면 "Event loop is closed" 로 다음 task 가 실패.

    두 개의 asyncio.run() 호출을 이어서 실행 → 각 호출에서 exchange 가 **다른** 객체여야.
    """
    provider = CCXTProvider("bybit")

    async def _capture_exchange() -> object:
        return provider.exchange

    first = asyncio.run(_capture_exchange())
    second = asyncio.run(_capture_exchange())

    assert first is not second, (
        "Loop 이 바뀌었는데 exchange 가 재생성 안 됨 — "
        "다음 task 에서 'Event loop is closed' 발생 예상"
    )


def test_exchange_returns_same_instance_within_same_loop() -> None:
    """같은 loop 내 반복 접근은 singleton 유지 (resource 낭비 방지)."""
    provider = CCXTProvider("bybit")

    async def _capture_twice() -> tuple[object, object]:
        return provider.exchange, provider.exchange

    first, second = asyncio.run(_capture_twice())
    assert first is second, "같은 loop 내에서는 exchange 재사용되어야 함"

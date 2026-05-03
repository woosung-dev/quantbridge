"""CCXTProvider.fetch_ohlcv `limit_bars` 모드 (Sprint 26 B.3, codex P1 #6).

검증:
- limit_bars=N → bars 길이 ≤ N + 모든 bar closed (now 기준 last_closed 이하)
- since/until 동시 지정 시 무시 + WARN log
- 305 bar over-fetch → slice 후 정확히 limit_bars 개
- 1h timeframe + limit_bars=10 → since = now - 12h (정확성)
- limit_bars=None + since/until 둘 다 None → ValueError
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.market_data.providers.ccxt import CCXTProvider


@pytest.mark.asyncio
async def test_limit_bars_returns_at_most_n_closed_bars(monkeypatch) -> None:
    """limit_bars=300 → 길이 ≤ 300 + 모두 last_closed_ts 이하."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    tf_sec = 60  # 1m
    # 320 bars: 마지막 1개는 진행 중, 나머지는 closed
    bars = [
        [now_ms - (320 - i) * tf_sec * 1000, 1, 2, 0, 1, 10]
        for i in range(320)
    ]
    monkeypatch.setattr(provider, "_fetch_page", AsyncMock(side_effect=[bars, []]))

    result = await provider.fetch_ohlcv("BTC/USDT", "1m", limit_bars=300)

    assert len(result) <= 300
    last_closed_ts = (now_ms // 1000 // tf_sec) * tf_sec - tf_sec
    assert all(b[0] <= last_closed_ts * 1000 for b in result)

    await provider.close()


@pytest.mark.asyncio
async def test_limit_bars_overrides_since_and_emits_warning(
    monkeypatch, caplog
) -> None:
    """limit_bars + since 동시 → since 무시 + WARN log."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr(provider, "_fetch_page", AsyncMock(return_value=[]))

    user_since = datetime(2020, 1, 1, tzinfo=UTC)
    user_until = datetime(2020, 1, 2, tzinfo=UTC)

    with caplog.at_level(logging.WARNING):
        await provider.fetch_ohlcv(
            "BTC/USDT", "1m", since=user_since, until=user_until, limit_bars=50
        )

    assert any(
        "ccxt_fetch_limit_bars_overrides_since_until" in record.getMessage()
        for record in caplog.records
    )

    # _fetch_page 의 since_ms 가 user_since (2020) 이 아니라 최근 (now - 52*60s) 인지 검증
    actual_call = provider._fetch_page.call_args  # type: ignore[attr-defined]
    actual_since_ms = actual_call.args[2] if actual_call.args else actual_call.kwargs["since_ms"]
    user_since_ms = int(user_since.timestamp() * 1000)
    assert actual_since_ms > user_since_ms + 365 * 24 * 3600 * 1000, (
        "limit_bars 모드인데 user_since 가 적용됨"
    )

    await provider.close()


@pytest.mark.asyncio
async def test_limit_bars_slices_overfetched_pages(monkeypatch) -> None:
    """exchange 가 305 bar 반환 → slice 후 정확히 300 + 마지막 closed."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    tf_sec = 60
    # 305 closed bars (모두 last_closed_ts 이하)
    bars = [
        [now_ms - (310 - i) * tf_sec * 1000, 1, 2, 0, 1, 10]
        for i in range(305)
    ]
    monkeypatch.setattr(provider, "_fetch_page", AsyncMock(side_effect=[bars, []]))

    result = await provider.fetch_ohlcv("BTC/USDT", "1m", limit_bars=300)

    assert len(result) == 300
    # 마지막 bar 가 closed
    last_closed_ts = (now_ms // 1000 // tf_sec) * tf_sec - tf_sec
    assert result[-1][0] <= last_closed_ts * 1000
    # 가장 최근 (slice 후 첫 → 마지막) 순서 유지
    assert result[0][0] < result[-1][0]

    await provider.close()


@pytest.mark.asyncio
async def test_limit_bars_computes_since_for_1h_timeframe(monkeypatch) -> None:
    """limit_bars=10, 1h → since = now - 12h (== (10+2) * 3600s) 정확성."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    fetch_spy = AsyncMock(return_value=[])
    monkeypatch.setattr(provider, "_fetch_page", fetch_spy)

    before_ms = int(datetime.now(UTC).timestamp() * 1000)
    await provider.fetch_ohlcv("BTC/USDT", "1h", limit_bars=10)
    after_ms = int(datetime.now(UTC).timestamp() * 1000)

    # _fetch_page(symbol, timeframe, since_ms, limit) 의 since_ms 검증
    actual_since_ms = fetch_spy.call_args.args[2]
    expected_since_ms_lower = before_ms - 12 * 3600 * 1000
    expected_since_ms_upper = after_ms - 12 * 3600 * 1000

    # 12h before now ± 호출 시간차
    assert expected_since_ms_lower - 1000 <= actual_since_ms <= expected_since_ms_upper + 1000

    await provider.close()


@pytest.mark.asyncio
async def test_fetch_ohlcv_requires_since_or_limit_bars(monkeypatch) -> None:
    """since/until/limit_bars 모두 None → ValueError."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    with pytest.raises(ValueError, match=r"since.*until.*limit_bars"):
        await provider.fetch_ohlcv("BTC/USDT", "1m")

    await provider.close()


@pytest.mark.asyncio
async def test_legacy_since_until_pagination_still_works(monkeypatch) -> None:
    """기존 회귀: limit_bars=None + since/until → 기존 pagination 유지."""
    provider = CCXTProvider("bybit")
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    base_ms = 1_704_067_200_000  # 2024-01-01 UTC (충분히 과거)
    page1 = [[base_ms + i * 60_000, 1, 2, 0, 1, 1] for i in range(500)]
    monkeypatch.setattr(provider, "_fetch_page", AsyncMock(side_effect=[page1, []]))

    since = datetime(2024, 1, 1, tzinfo=UTC)
    until = datetime(2024, 1, 2, tzinfo=UTC)
    result = await provider.fetch_ohlcv("BTC/USDT", "1m", since, until)

    assert len(result) == 500
    assert result[0][0] == base_ms
    # limit_bars 없으므로 slice 안 일어남 (full pagination)

    await provider.close()

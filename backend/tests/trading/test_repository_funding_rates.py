# FundingRateRepository.get_funding_series — window clip + 거래소/심볼 필터 + tz-aware Decimal Series 검증.
"""FundingRateRepository (Slice 4 perp funding 배선) — DB-backed read 검증.

backtest 엔진이 perp funding 을 차감하려면 funding_rates 를 [period_start, period_end]
구간으로 clip 해 읽어야 한다. raw-SQL 인제스션만 있던 trading.funding_rates 에
read 메서드(get_funding_series)를 추가한다. 시드 → BETWEEN window clip + 필터 +
tz-aware DatetimeIndex + Decimal value(float 금지) + 빈 결과 처리.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd


async def test_get_funding_series_window_clip_and_filter(db_session) -> None:
    from src.trading.models import ExchangeName, FundingRate
    from src.trading.repositories.funding_rate_repository import FundingRateRepository

    base = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        FundingRate(exchange=ExchangeName.bybit, symbol="BTC/USDT:USDT",
                    funding_rate=Decimal("0.0001"), funding_timestamp=base),
        FundingRate(exchange=ExchangeName.bybit, symbol="BTC/USDT:USDT",
                    funding_rate=Decimal("0.0002"), funding_timestamp=base + timedelta(hours=8)),
        FundingRate(exchange=ExchangeName.bybit, symbol="BTC/USDT:USDT",
                    funding_rate=Decimal("0.0003"), funding_timestamp=base + timedelta(hours=16)),
        # 다른 심볼 — 제외
        FundingRate(exchange=ExchangeName.bybit, symbol="ETH/USDT:USDT",
                    funding_rate=Decimal("0.9"), funding_timestamp=base + timedelta(hours=8)),
        # 다른 거래소 — 제외
        FundingRate(exchange=ExchangeName.binance, symbol="BTC/USDT:USDT",
                    funding_rate=Decimal("0.9"), funding_timestamp=base + timedelta(hours=8)),
        # window 밖(end 초과) — BETWEEN 으로 제외
        FundingRate(exchange=ExchangeName.bybit, symbol="BTC/USDT:USDT",
                    funding_rate=Decimal("0.5"), funding_timestamp=base + timedelta(hours=48)),
    ]
    for r in rows:
        db_session.add(r)
    await db_session.commit()

    repo = FundingRateRepository(db_session)
    series = await repo.get_funding_series(
        exchange="bybit",
        symbol="BTC/USDT:USDT",
        start=base,
        end=base + timedelta(hours=16),
    )

    # [00:00, 16:00] inclusive → bybit BTC 3 rows 만, ascending.
    assert len(series) == 3
    assert list(series.values) == [Decimal("0.0001"), Decimal("0.0002"), Decimal("0.0003")]
    # tz-aware DatetimeIndex + Decimal value (float 금지).
    assert series.index.tz is not None
    assert series.index[0] == pd.Timestamp(base)
    assert all(isinstance(v, Decimal) for v in series.values)


async def test_get_funding_series_empty_when_no_match(db_session) -> None:
    from src.trading.repositories.funding_rate_repository import FundingRateRepository

    repo = FundingRateRepository(db_session)
    series = await repo.get_funding_series(
        exchange="bybit",
        symbol="DOGE/USDT:USDT",
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )
    assert isinstance(series, pd.Series)
    assert len(series) == 0

"""TimescaleProvider 경로로 backtest 데이터 플로우 E2E 검증 (mock CCXT).

실제 Celery task / HTTP endpoint는 우회 — provider 경로의 correctness 확인이
주 목적. Celery + ccxt 실 배선은 Sprint 5 Stage B 이후 L4 smoke test에서 검증.
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.repository import OHLCVRepository


@pytest.mark.asyncio
async def test_backtest_with_timescale_provider_cache_miss_then_hit(
    db_session,
) -> None:
    """cache miss → CCXT fetch → DB 저장 → 재호출 시 cache hit (CCXT 재호출 0)."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    hours = 168  # 1주일 1h bar

    # mock CCXT: 1주일치 합성 OHLCV
    base_ms = int(base.timestamp() * 1000)
    mock_bars = [
        [
            base_ms + i * 3_600_000,
            100.0 + i,
            105.0 + i,
            95.0 + i,
            102.0 + i,
            1000.0,
        ]
        for i in range(hours)
    ]
    mock_ccxt = AsyncMock(spec=CCXTProvider)
    mock_ccxt.fetch_ohlcv.return_value = mock_bars

    repo = OHLCVRepository(db_session)
    provider = TimescaleProvider(repo, mock_ccxt, exchange_name="bybit")

    # 1차 호출 — cache miss, CCXT fetch
    df1 = await provider.get_ohlcv(
        "BTC/USDT", "1h", base, base + timedelta(hours=hours - 1)
    )
    assert len(df1) == hours
    assert list(df1.columns) == ["open", "high", "low", "close", "volume"]
    assert mock_ccxt.fetch_ohlcv.call_count == 1

    # DB에 실제 insert됐는지 확인
    cached = await repo.get_range(
        "BTC/USDT", "1h", base, base + timedelta(hours=hours - 1)
    )
    assert len(cached) == hours

    # 2차 호출 — cache hit, CCXT 재호출 0
    df2 = await provider.get_ohlcv(
        "BTC/USDT", "1h", base, base + timedelta(hours=hours - 1)
    )
    assert len(df2) == hours
    # 1차와 동일 call count (2차는 CCXT fetch 안 함)
    assert mock_ccxt.fetch_ohlcv.call_count == 1


@pytest.mark.asyncio
async def test_timescale_provider_respects_ohlcv_provider_flag(
    monkeypatch, db_session
) -> None:
    """settings.ohlcv_provider='timescale' 분기 확인 — build_backtest_service_for_worker."""
    monkeypatch.setattr(
        "src.core.config.settings.ohlcv_provider", "timescale"
    )

    # worker singleton을 mock으로 교체. src.tasks.__init__이 Celery 인스턴스를
    # 동일한 이름 `celery_app`으로 re-export해서 `import src.tasks.celery_app`이
    # 인스턴스로 해석되는 문제 — importlib로 submodule 객체를 명시적 획득.
    mock_ccxt = AsyncMock(spec=CCXTProvider)
    from importlib import import_module

    celery_module = import_module("src.tasks.celery_app")
    monkeypatch.setattr(
        celery_module, "get_ccxt_provider_for_worker", lambda: mock_ccxt
    )

    from src.backtest.dependencies import build_backtest_service_for_worker

    service = build_backtest_service_for_worker(db_session)
    # BacktestService는 provider를 self.provider로 보관 (service.py:64)
    assert isinstance(service.provider, TimescaleProvider)
    assert service.provider.ccxt is mock_ccxt
    assert service.provider.exchange_name == "bybit"

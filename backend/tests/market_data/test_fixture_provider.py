"""FixtureProvider — CSV 로드 + 기간 필터."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.exceptions import OHLCVFixtureNotFound
from src.market_data.providers import OHLCVProvider
from src.market_data.providers.fixture import FixtureProvider


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    """임시 fixture 디렉토리 + 미니 CSV."""
    root = tmp_path / "ohlcv"
    root.mkdir()
    csv = root / "BTCUSDT_1h.csv"
    csv.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01T00:00:00Z,100.0,101.0,99.0,100.5,10.0\n"
        "2024-01-01T01:00:00Z,100.5,102.0,100.0,101.5,11.0\n"
        "2024-01-01T02:00:00Z,101.5,103.0,101.0,102.5,12.0\n"
        "2024-01-01T03:00:00Z,102.5,104.0,102.0,103.5,13.0\n"
    )
    return root


class TestFixtureProvider:
    def test_satisfies_protocol(self, fixture_root: Path) -> None:
        provider: OHLCVProvider = FixtureProvider(root=fixture_root)
        assert provider is not None

    @pytest.mark.asyncio
    async def test_get_ohlcv_full_range(self, fixture_root: Path) -> None:
        provider = FixtureProvider(root=fixture_root)
        df = await provider.get_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, 0, 0, 0),
            period_end=datetime(2024, 1, 1, 3, 0, 0),
        )
        assert len(df) == 4
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(df.index, pd.DatetimeIndex)

    @pytest.mark.asyncio
    async def test_period_filter(self, fixture_root: Path) -> None:
        provider = FixtureProvider(root=fixture_root)
        df = await provider.get_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, 1, 0, 0),
            period_end=datetime(2024, 1, 1, 2, 0, 0),
        )
        assert len(df) == 2

    @pytest.mark.asyncio
    async def test_missing_file_raises(self, fixture_root: Path) -> None:
        provider = FixtureProvider(root=fixture_root)
        with pytest.raises(OHLCVFixtureNotFound):
            await provider.get_ohlcv(
                symbol="ETHUSDT",
                timeframe="1h",
                period_start=datetime(2024, 1, 1),
                period_end=datetime(2024, 1, 2),
            )

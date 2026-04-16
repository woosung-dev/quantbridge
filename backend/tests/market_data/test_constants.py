import pytest

from src.market_data.constants import (
    TIMEFRAME_SECONDS,
    VALID_TIMEFRAMES,
    normalize_symbol,
)


def test_valid_timeframes() -> None:
    assert frozenset({"1m", "5m", "15m", "1h", "4h", "1d"}) == VALID_TIMEFRAMES


def test_timeframe_seconds_consistency() -> None:
    assert TIMEFRAME_SECONDS["1m"] == 60
    assert TIMEFRAME_SECONDS["5m"] == 300
    assert TIMEFRAME_SECONDS["15m"] == 900
    assert TIMEFRAME_SECONDS["1h"] == 3600
    assert TIMEFRAME_SECONDS["4h"] == 14400
    assert TIMEFRAME_SECONDS["1d"] == 86400


def test_normalize_symbol_already_unified() -> None:
    assert normalize_symbol("BTC/USDT") == "BTC/USDT"
    assert normalize_symbol("eth/usdt") == "ETH/USDT"


def test_normalize_symbol_concatenated() -> None:
    assert normalize_symbol("BTCUSDT") == "BTC/USDT"
    assert normalize_symbol("ETHUSDC") == "ETH/USDC"
    assert normalize_symbol("SOLUSD") == "SOL/USD"


def test_normalize_symbol_invalid() -> None:
    with pytest.raises(ValueError, match="Cannot normalize"):
        normalize_symbol("BTC")

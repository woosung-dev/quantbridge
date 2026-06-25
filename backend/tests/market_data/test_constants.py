import pytest

from src.market_data.constants import (
    TIMEFRAME_SECONDS,
    VALID_TIMEFRAMES,
    normalize_symbol,
    to_ccxt_perpetual_symbol,
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


def test_to_ccxt_perpetual_symbol_from_unified() -> None:
    # USDT-margined perp = settle 가 quote 와 동일 → "BASE/QUOTE:QUOTE".
    assert to_ccxt_perpetual_symbol("BTC/USDT") == "BTC/USDT:USDT"
    assert to_ccxt_perpetual_symbol("ETH/USDT") == "ETH/USDT:USDT"
    assert to_ccxt_perpetual_symbol("eth/usdt") == "ETH/USDT:USDT"


def test_to_ccxt_perpetual_symbol_from_concatenated() -> None:
    # normalize_symbol 재사용 → slash 추가 후 colon settle 부착.
    assert to_ccxt_perpetual_symbol("BTCUSDT") == "BTC/USDT:USDT"
    assert to_ccxt_perpetual_symbol("ETHUSDC") == "ETH/USDC:USDC"


def test_to_ccxt_perpetual_symbol_idempotent() -> None:
    # 이미 colon perp 면 그대로(대문자만).
    assert to_ccxt_perpetual_symbol("BTC/USDT:USDT") == "BTC/USDT:USDT"
    assert to_ccxt_perpetual_symbol("btc/usdt:usdt") == "BTC/USDT:USDT"


def test_to_ccxt_perpetual_symbol_invalid() -> None:
    with pytest.raises(ValueError, match="Cannot normalize"):
        to_ccxt_perpetual_symbol("BTC")

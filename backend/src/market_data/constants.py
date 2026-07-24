"""market_data 도메인 상수 — Timeframe enum + Symbol 정규화."""
from typing import Literal, get_args

Timeframe = Literal["1m", "5m", "15m", "1h", "4h", "1d"]

TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

VALID_TIMEFRAMES: frozenset[str] = frozenset(get_args(Timeframe))


def normalize_symbol(symbol: str) -> str:
    """CCXT unified format으로 정규화. 'BTCUSDT' → 'BTC/USDT'.

    이미 unified면 대문자만 적용. quote 우선순위는 길이 긴 것부터
    (USDT/USDC가 USD보다 먼저 매칭되도록).
    """
    if "/" in symbol:
        return symbol.upper()
    upper = symbol.upper()
    for quote in ("USDT", "USDC", "USD", "BTC", "ETH"):
        if upper.endswith(quote):
            base = upper[: -len(quote)]
            if base:
                return f"{base}/{quote}"
    raise ValueError(f"Cannot normalize symbol: {symbol}")


def to_ccxt_perpetual_symbol(symbol: str) -> str:
    """unified/concat 심볼 → CCXT USDT-margined perpetual ('BTC/USDT:USDT').

    backtest 심볼('BTC/USDT')과 funding 인제스션 심볼('BTC/USDT:USDT', CCXT perp
    colon 포맷) 사이의 브릿지. settle 통화 = quote 통화(USDT-margined). 이미 colon
    perp 면 대문자만 적용(idempotent). normalize 불가 심볼은 ValueError 전파.
    """
    if ":" in symbol:
        return symbol.upper()
    unified = normalize_symbol(symbol)
    quote = unified.split("/")[1]
    return f"{unified}:{quote}"


def to_bybit_raw_symbol(symbol: str) -> str:
    """CCXT unified/perp 심볼 → Bybit raw 심볼 ('BTCUSDT').

    CCXT perpetual settle 통화는 제거하고 slash도 제거한다.
    """
    return symbol.split(":", maxsplit=1)[0].replace("/", "").upper()

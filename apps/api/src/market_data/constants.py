"""market_data 도메인 상수 — Timeframe enum + Symbol 정규화."""
from typing import Literal, get_args

# BL-454 — `normalize_symbol` 은 `src/common/normalized_symbol.py` 로 이동했다.
# `src/common` 이 도메인 모듈을 import 하지 않는다는 방향을 지키면서 trading ingress 가
# 같은 구현을 쓰게 하려면 여기가 아니라 common 에 있어야 한다. 기존 소비처
# (`backtest/service.py`, `market_data/providers/timescale.py`, 아래 두 헬퍼)를 위해
# 이름은 그대로 재수출한다.
from src.common.normalized_symbol import normalize_symbol

__all__ = [
    "TIMEFRAME_SECONDS",
    "VALID_TIMEFRAMES",
    "Timeframe",
    "normalize_symbol",
    "to_bybit_raw_symbol",
    "to_ccxt_perpetual_symbol",
]

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

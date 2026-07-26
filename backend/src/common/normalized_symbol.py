# BL-454 — 거래 심볼을 요청 경계에서 한 번 정규화하는 도메인 프리미티브.

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BeforeValidator

# CCXT unified spot 표기만 canonical 로 인정한다. `BTC/USDT` / `1000PEPE/USDT` 통과,
# `BTC/USDT.P` / `BYBIT:BTCUSDT` / `BTC-USDT` reject.
_UNIFIED_SYMBOL_RE = re.compile(r"^[A-Z0-9]{1,16}/[A-Z0-9]{1,15}$")

# `Order.symbol` / `LiveSignalSession.symbol` / `ExchangeExit.symbol` 컬럼 폭.
_SYMBOL_MAX_LENGTH = 32

# quote 우선순위는 길이 긴 것부터 — USDT/USDC 가 USD 보다 먼저 매칭돼야 한다.
_QUOTES: tuple[str, ...] = ("USDT", "USDC", "USD", "BTC", "ETH")


def normalize_symbol(symbol: str) -> str:
    """CCXT unified format으로 정규화. 'BTCUSDT' → 'BTC/USDT'.

    이미 unified면 대문자만 적용. quote 우선순위는 길이 긴 것부터
    (USDT/USDC가 USD보다 먼저 매칭되도록).

    ★관대함을 유지한다. `backtest`·`market_data` 가 이미 저장된 값에 이 함수를 쓰므로
    (`backtest/service.py`, `market_data/providers/timescale.py`) 여기를 엄격하게 만들면
    기존 데이터의 동작이 바뀐다. 요청 경계 강화는 `normalize_symbol_input` 에만 있다.
    """
    if "/" in symbol:
        return symbol.upper()
    upper = symbol.upper()
    for quote in _QUOTES:
        if upper.endswith(quote):
            base = upper[: -len(quote)]
            if base:
                return f"{base}/{quote}"
    raise ValueError(f"Cannot normalize symbol: {symbol}")


def normalize_symbol_input(v: object) -> str:
    """Request-boundary 전용 심볼 validator.

    두 ingress(라이브 세션 등록 · TradingView 웹훅)가 **같은 이 함수**를 쓴다. 정규화
    구현이 두 곳으로 갈리는 것이 BL-454 가 지적한 결함 그 자체이므로 복제하지 않는다.

    canonical 은 `BTC/USDT`(CCXT unified spot)이고 이는 선택이 아니라 강제다 —
    `providers._to_bybit_linear_symbol` 이 `:USDT` 를 합성하는데 그 함수가
    `"/" not in symbol` 이면 원문을 그대로 통과시키므로, 원문 `BTCUSDT` 는 linear
    어댑터를 **우회**한다. 즉 미정규화 심볼이 조용히 잘못된 market 으로 라우팅된다.

    ★인식 못 하는 표기는 통과시키지 않고 거부한다(fail-closed). TradingView 가
    `{{ticker}}` 로 정확히 무엇을 보내는지(`BTCUSDT` 인지 `BTCUSDT.P` 인지) 1차 출처로
    확인하지 못했으므로, `.P`/`PERP`/거래소 접두 같은 장식 제거를 **추측으로 넣지 않는다.**
    대신 거부를 카운터와 로그로 관측해 첫 실사용 때 실제 포맷을 배운다.
    """
    if not isinstance(v, str):
        raise ValueError(
            f"symbol must be a string (got {type(v).__name__}). "
            "숫자·객체 입력은 요청 경계에서 거부한다."
        )
    s = v.strip()
    if not s:
        raise ValueError("symbol must not be empty")

    if ":" in s:
        # CCXT perpetual 표기(`BTC/USDT:USDT`). settle 통화가 quote 와 같을 때만
        # linear 로 붕괴시킨다. `BTC/USD:BTC`(inverse/coin-margined)를 조용히
        # linear 로 강제하면 완전히 다른 시장이 된다.
        # ★slash 없는 콜론 입력(`BTCUSDT:USDT`)도 여기서 처리해야 한다 —
        # `normalize_symbol` 에 그대로 넣으면 `BTCUSDT:/USDT` 라는 쓰레기가 나온다.
        market, _, settle = s.partition(":")
        unified = normalize_symbol(market)
        quote = unified.split("/")[1]
        if settle.upper() != quote:
            raise ValueError(
                f"settle currency {settle!r} does not match quote {quote!r} (got {v!r}). "
                "inverse/coin-margined 심볼은 linear 로 정규화하지 않는다."
            )
        s = unified
    else:
        s = normalize_symbol(s)

    if not _UNIFIED_SYMBOL_RE.fullmatch(s):
        # `normalize_symbol` 은 slash 가 있으면 대문자화만 하고 통과시키므로
        # `BTC/USDT.P` 같은 장식이 그 구멍으로 들어온다. 여기서 닫는다.
        raise ValueError(
            f"symbol is not a CCXT unified market (got {v!r} → {s!r}). "
            "`BASE/QUOTE` 형식만 허용한다."
        )
    if len(s) > _SYMBOL_MAX_LENGTH:
        # 정규화는 길이를 늘린다(`BTCUSDT` 7 → `BTC/USDT` 8). 컬럼 폭은 정규화
        # **후** 값에 걸려야 하므로 여기서도 확인한다.
        raise ValueError(f"symbol exceeds {_SYMBOL_MAX_LENGTH} characters after normalization: {s!r}")
    return s


NormalizedSymbol = Annotated[str, BeforeValidator(normalize_symbol_input)]
"""Request-boundary 전용 canonical 심볼 type.

사용: `symbol: NormalizedSymbol = Field(min_length=1, max_length=32)`
(`trading/schemas.py` RegisterLiveSessionRequest).

`BeforeValidator` 이므로 str 길이 제약보다 **먼저** 돌아 제약이 정규화 후 값에 걸린다.
미인식 표기는 `ValueError` → FastAPI 가 422 로 변환한다(신규 예외 배관 불필요).
"""

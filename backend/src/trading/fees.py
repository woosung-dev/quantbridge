"""거래소 수수료 스케줄 — Bybit USDT Perpetual VIP 0~5+ 인라인 상수.

확장 방법:
- 신규 거래소: _FEES dict에 exchange key 추가.
- VIP 갱신: Bybit 공식 Fees 페이지 참조 (https://www.bybit.com/en/fee/tradeInfo).
- BacktestEngine 연동: get_fee() 반환값을 거래대금에 곱해 수수료 산출.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

# Bybit USDT Perpetual 수수료 (VIP tier 0~6).
# 출처: Bybit 공식 수수료 페이지 2026-04 기준.
# VIP 5 이상은 OTC/맞춤 협상 — 공개 tier 최고값(VIP 5) 사용.
_BYBIT_PERP_FEES: dict[int, dict[str, Decimal]] = {
    0: {"maker": Decimal("0.0002"),  "taker": Decimal("0.00055")},
    1: {"maker": Decimal("0.0002"),  "taker": Decimal("0.00050")},
    2: {"maker": Decimal("0.0001"),  "taker": Decimal("0.00045")},
    3: {"maker": Decimal("0.0000"),  "taker": Decimal("0.00040")},
    4: {"maker": Decimal("-0.0001"), "taker": Decimal("0.00035")},
    5: {"maker": Decimal("-0.0001"), "taker": Decimal("0.00030")},
}
_BYBIT_PERP_MAX_TIER = 5

_FEES: dict[str, dict[int, dict[str, Decimal]]] = {
    "bybit": _BYBIT_PERP_FEES,
}


def get_fee(
    exchange: str,
    tier: int,
    side: Literal["maker", "taker"],
) -> Decimal:
    """거래소·VIP tier·maker/taker에 대한 수수료율(소수) 반환.

    음수는 maker rebate를 의미한다 (e.g. Bybit VIP 4+).

    Args:
        exchange: 거래소 식별자. 현재 지원: "bybit".
        tier: VIP tier (0 이상). tier > max는 max로 clamp.
        side: "maker" 또는 "taker".

    Returns:
        수수료율 Decimal (예: 0.00055 = 0.055%).

    Raises:
        ValueError: 지원하지 않는 exchange.
    """
    if exchange not in _FEES:
        raise ValueError(f"Unsupported exchange for fee lookup: {exchange!r}. Supported: {list(_FEES)}")
    schedule = _FEES[exchange]
    clamped = min(tier, _BYBIT_PERP_MAX_TIER)
    return schedule[clamped][side]

# Pine v2 격리 레버리지 증거금과 청산가를 계산하는 순수 함수.
"""Bybit 기준 isolated 청산가와 증거금을 계산한다.

플랫 MMR 0.5%와 단일 tier를 적용한 Bybit 기준 isolated 모델이다. 파산수수료,
펀딩, tier 계단은 반영하지 않으며 BL-186b에서 확장한다.

``src.trading.liquidation.calculate_liquidation_price``를 재사용하지 않는다. 해당
함수는 거래소 주문 모양인 ``OrderSide`` enum, ``int`` leverage, ``Decimal`` 계약인
반면, pine_v2는 소수 배수(예: 2.5x)를 허용하는 ``float``와 ``Direction`` 리터럴
계약이다. 도메인 경계 역행을 피하기 위해 이관했고, 수식 일치는 parity 테스트가
강제한다.

레버리지는 주문 수량을 바꾸지 않는다. TradingView와 MT5 컨벤션에 따라 필요
증거금과 청산가만 결정한다.
"""

from __future__ import annotations

import math
from typing import Literal

Direction = Literal["long", "short"]

MAINTENANCE_MARGIN_RATE: float = 0.005
MARGIN_BUFFER: float = 0.95


def is_leverage_active(leverage: float) -> bool:
    """레버리지 적용 여부의 단일 게이트 술어를 반환한다."""
    return math.isfinite(leverage) and leverage > 1.0


def liquidation_price(
    *,
    entry_price: float,
    direction: Direction,
    leverage: float,
    mmr: float = MAINTENANCE_MARGIN_RATE,
) -> float | None:
    """진입가, 방향, 레버리지, MMR로 isolated 청산가를 계산한다."""
    if (
        entry_price <= 0
        or leverage <= 0
        or not all(math.isfinite(value) for value in (entry_price, leverage, mmr))
    ):
        return None

    initial_margin_rate = 1 / leverage
    if direction == "long":
        return entry_price * (1 - initial_margin_rate + mmr)
    return entry_price * (1 + initial_margin_rate - mmr)


def required_margin(*, qty: float, price: float, leverage: float) -> float:
    """주문 수량을 바꾸지 않은 채 필요한 초기 증거금을 계산한다."""
    if leverage <= 0:
        return math.inf
    return qty * price / leverage


def margin_available_ok(
    *, required: float, available: float, buffer: float = MARGIN_BUFFER
) -> bool:
    """버퍼를 적용한 가용 증거금이 필요 증거금 이상인지 반환한다."""
    return required <= available * buffer

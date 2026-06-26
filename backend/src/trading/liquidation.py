"""청산가 순수 계산기 — Bybit USDT 무기한(linear) isolated, on-the-fly 계산 (모델/마이그레이션 0).

공식 (단일 tier 단순화):
- IMR(initial margin rate) = 1 / leverage
- Long(buy)  liq = entry × (1 − IMR + MMR)
- Short(sell) liq = entry × (1 + IMR − MMR)

MMR(maintenance margin rate) 출처 = ccxt market leverage tier `maintenanceMarginRate`
(Bybit raw `maintenanceMargin`, ccxt 4.5.49 bybit.py:8217). **fraction 표기 강제**
(0.005 = 0.5%). 단일 tier 상수 사용 — tier 테이블/펀딩/수수료/파산수수료는 미반영(follow-up).

Decimal 전구간(float 금지). 경계 위반은 거래소 거부와 동일 의미로 ValueError.
"""

from __future__ import annotations

from decimal import Decimal

from src.trading.models import OrderSide

# BTCUSDT 최저위험 tier 의 maintenance margin = 0.5% = fraction 0.005.
# Bybit risk-limit tier 표를 미반영한 단일 tier 단순화 (정직 고지 대상).
DEFAULT_MAINTENANCE_MARGIN_RATE = Decimal("0.005")


def calculate_liquidation_price(
    *,
    entry_price: Decimal,
    side: OrderSide,
    leverage: int,
    maintenance_margin_rate: Decimal = DEFAULT_MAINTENANCE_MARGIN_RATE,
) -> Decimal:
    """진입가/방향/레버리지/MMR 로 isolated 청산가 계산 (Bybit USDT linear).

    Args:
        entry_price: 진입가 (Decimal, > 0).
        side: 포지션 방향 (buy=long / sell=short).
        leverage: 레버리지 배수 (int, > 0).
        maintenance_margin_rate: 유지증거금률 (fraction, >= 0. 0.005 = 0.5%).

    Returns:
        청산가 (Decimal).

    Raises:
        ValueError: leverage <= 0, entry_price <= 0, maintenance_margin_rate < 0.
    """
    if leverage <= 0:
        raise ValueError("leverage must be a positive integer")
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if maintenance_margin_rate < 0:
        raise ValueError("maintenance_margin_rate must be non-negative")

    initial_margin_rate = Decimal(1) / Decimal(leverage)

    if side is OrderSide.buy:
        factor = Decimal(1) - initial_margin_rate + maintenance_margin_rate
    else:
        factor = Decimal(1) + initial_margin_rate - maintenance_margin_rate

    return entry_price * factor


def liquidation_distance_pct(
    *,
    entry_price: Decimal,
    liquidation_price: Decimal,
) -> Decimal:
    """진입가 대비 청산가까지의 거리 퍼센트 = |liq − entry| / entry × 100.

    Raises:
        ValueError: entry_price <= 0.
    """
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    return abs(liquidation_price - entry_price) / entry_price * Decimal(100)

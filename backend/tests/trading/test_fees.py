"""수수료 스케줄 단위 테스트 — 순수 unit, DB 없음."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.trading.fees import get_fee


# ---------------------------------------------------------------------------
# Bybit VIP 0 (기본 tier)
# ---------------------------------------------------------------------------

def test_bybit_vip0_taker():
    assert get_fee("bybit", 0, "taker") == Decimal("0.00055")


def test_bybit_vip0_maker():
    assert get_fee("bybit", 0, "maker") == Decimal("0.0002")


# ---------------------------------------------------------------------------
# Maker rebate (VIP 4+)
# ---------------------------------------------------------------------------

def test_bybit_vip4_maker_is_negative():
    fee = get_fee("bybit", 4, "maker")
    assert fee < Decimal("0"), "VIP 4 maker은 rebate(음수)여야 함"


def test_bybit_vip5_maker_is_negative():
    fee = get_fee("bybit", 5, "maker")
    assert fee < Decimal("0")


# ---------------------------------------------------------------------------
# Tier clamp
# ---------------------------------------------------------------------------

def test_tier_above_max_clamped_to_max():
    """VIP 999는 VIP 5와 동일 수수료 반환."""
    assert get_fee("bybit", 999, "taker") == get_fee("bybit", 5, "taker")
    assert get_fee("bybit", 999, "maker") == get_fee("bybit", 5, "maker")


def test_tier_0_equals_tier_1_for_maker():
    """VIP 0/1 maker는 동일 요율."""
    assert get_fee("bybit", 0, "maker") == get_fee("bybit", 1, "maker")


# ---------------------------------------------------------------------------
# 미지원 거래소
# ---------------------------------------------------------------------------

def test_unsupported_exchange_raises():
    with pytest.raises(ValueError, match="Unsupported exchange"):
        get_fee("binance", 0, "taker")


# ---------------------------------------------------------------------------
# 수수료 단조 감소 (VIP 올라갈수록 저렴)
# ---------------------------------------------------------------------------

def test_bybit_taker_fee_monotone_decreasing():
    """taker 수수료는 VIP 올라갈수록 단조 감소."""
    prev = get_fee("bybit", 0, "taker")
    for tier in range(1, 6):
        curr = get_fee("bybit", tier, "taker")
        assert curr <= prev, f"taker fee at tier {tier} should be <= tier {tier-1}"
        prev = curr

# 청산가 순수 계산기 손계산 oracle 테스트 (Bybit USDT perp, circular 금지)

from __future__ import annotations

from decimal import Decimal

import pytest

from src.trading.liquidation import (
    DEFAULT_MAINTENANCE_MARGIN_RATE,
    calculate_liquidation_price,
    liquidation_distance_pct,
)
from src.trading.models import OrderSide


class TestLiquidationOracle:
    """손계산 oracle — 외부 hand-computed 값으로 검증 (엔진 결과 재사용 금지)."""

    @pytest.mark.parametrize(
        ("entry", "side", "leverage", "mmr", "expected"),
        [
            # Long: liq = entry × (1 − 1/lev + mmr)
            # 50000 × (1 − 0.1 + 0.005) = 50000 × 0.905 = 45250
            ("50000", OrderSide.buy, 10, "0.005", "45250"),
            # Short: liq = entry × (1 + 1/lev − mmr)
            # 50000 × (1 + 0.1 − 0.005) = 50000 × 1.095 = 54750
            ("50000", OrderSide.sell, 10, "0.005", "54750"),
            # Long, lev 20: 30000 × (1 − 0.05 + 0.005) = 30000 × 0.955 = 28650
            ("30000", OrderSide.buy, 20, "0.005", "28650"),
            # Short, lev 5, mmr 0.01: 30000 × (1 + 0.2 − 0.01) = 30000 × 1.19 = 35700
            ("30000", OrderSide.sell, 5, "0.01", "35700"),
            # Long, lev 1: 1000 × (1 − 1 + 0.005) = 1000 × 0.005 = 5
            ("1000", OrderSide.buy, 1, "0.005", "5"),
        ],
    )
    def test_hand_computed_liquidation_price(
        self, entry: str, side: OrderSide, leverage: int, mmr: str, expected: str
    ) -> None:
        result = calculate_liquidation_price(
            entry_price=Decimal(entry),
            side=side,
            leverage=leverage,
            maintenance_margin_rate=Decimal(mmr),
        )
        assert result == Decimal(expected)

    def test_result_is_decimal(self) -> None:
        result = calculate_liquidation_price(
            entry_price=Decimal("50000"),
            side=OrderSide.buy,
            leverage=10,
            maintenance_margin_rate=Decimal("0.005"),
        )
        assert isinstance(result, Decimal)

    def test_default_mmr_is_fraction(self) -> None:
        # BTCUSDT 최저위험 tier = 0.5% = fraction 0.005
        assert Decimal("0.005") == DEFAULT_MAINTENANCE_MARGIN_RATE


class TestLiquidationDistancePct:
    """청산가 거리 퍼센트 — |liq − entry| / entry × 100."""

    def test_long_distance(self) -> None:
        # (50000 − 45250) / 50000 × 100 = 9.5
        pct = liquidation_distance_pct(
            entry_price=Decimal("50000"), liquidation_price=Decimal("45250")
        )
        assert pct == Decimal("9.5")

    def test_short_distance(self) -> None:
        # (54750 − 50000) / 50000 × 100 = 9.5
        pct = liquidation_distance_pct(
            entry_price=Decimal("50000"), liquidation_price=Decimal("54750")
        )
        assert pct == Decimal("9.5")


class TestLiquidationEdgeCases:
    """경계 — 거래소 거부와 동일 의미로 ValueError."""

    def test_zero_leverage_raises(self) -> None:
        with pytest.raises(ValueError, match="leverage"):
            calculate_liquidation_price(
                entry_price=Decimal("50000"),
                side=OrderSide.buy,
                leverage=0,
                maintenance_margin_rate=Decimal("0.005"),
            )

    def test_negative_leverage_raises(self) -> None:
        with pytest.raises(ValueError, match="leverage"):
            calculate_liquidation_price(
                entry_price=Decimal("50000"),
                side=OrderSide.buy,
                leverage=-1,
                maintenance_margin_rate=Decimal("0.005"),
            )

    def test_zero_entry_raises(self) -> None:
        with pytest.raises(ValueError, match="entry_price"):
            calculate_liquidation_price(
                entry_price=Decimal("0"),
                side=OrderSide.buy,
                leverage=10,
                maintenance_margin_rate=Decimal("0.005"),
            )

    def test_negative_mmr_raises(self) -> None:
        with pytest.raises(ValueError, match="maintenance_margin_rate"):
            calculate_liquidation_price(
                entry_price=Decimal("50000"),
                side=OrderSide.buy,
                leverage=10,
                maintenance_margin_rate=Decimal("-0.001"),
            )

    def test_distance_pct_zero_entry_raises(self) -> None:
        with pytest.raises(ValueError, match="entry_price"):
            liquidation_distance_pct(
                entry_price=Decimal("0"), liquidation_price=Decimal("45250")
            )

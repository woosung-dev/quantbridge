"""JSONB serialization helpers — Decimal + datetime."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestMetrics
from src.backtest.serializers import (
    _parse_utc_iso,
    _utc_iso,
    equity_curve_from_jsonb,
    equity_curve_to_jsonb,
    metrics_from_jsonb,
    metrics_to_jsonb,
)


class TestUtcIso:
    def test_naive_utc_to_z(self) -> None:
        dt = datetime(2024, 1, 1, 12, 34, 56)
        assert _utc_iso(dt) == "2024-01-01T12:34:56Z"

    def test_roundtrip(self) -> None:
        """_parse_utc_iso는 tz-aware UTC datetime 반환 (Sprint 5 Stage B)."""
        original = datetime(2024, 6, 15, 9, 0, 0, tzinfo=UTC)
        assert _parse_utc_iso(_utc_iso(original)) == original

    def test_tz_aware_normalized(self) -> None:
        """tz-aware datetime도 방어적으로 naive UTC로 변환."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert _utc_iso(dt) == "2024-01-01T12:00:00Z"


class TestMetricsSerialization:
    def test_to_jsonb(self) -> None:
        m = BacktestMetrics(
            total_return=Decimal("0.18"),
            sharpe_ratio=Decimal("1.4"),
            max_drawdown=Decimal("-0.08"),
            win_rate=Decimal("0.56"),
            num_trades=24,
        )
        data = metrics_to_jsonb(m)
        assert data == {
            "total_return": "0.18",
            "sharpe_ratio": "1.4",
            "max_drawdown": "-0.08",
            "win_rate": "0.56",
            "num_trades": 24,
        }

    def test_roundtrip(self) -> None:
        m = BacktestMetrics(
            total_return=Decimal("0.1234"),
            sharpe_ratio=Decimal("2.0"),
            max_drawdown=Decimal("-0.05"),
            win_rate=Decimal("0.6"),
            num_trades=10,
        )
        restored = metrics_from_jsonb(metrics_to_jsonb(m))
        assert restored == m


class TestMetricsSerializationExtended:
    def test_none_fields_omitted_from_jsonb(self) -> None:
        """None 확장 필드는 JSONB dict에서 키 생략."""
        m = BacktestMetrics(
            total_return=Decimal("0.1"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("-0.05"),
            win_rate=Decimal("0.6"),
            num_trades=10,
            sortino_ratio=None,
        )
        d = metrics_to_jsonb(m)
        assert "sortino_ratio" not in d
        assert d["num_trades"] == 10

    def test_backward_compat_old_jsonb(self) -> None:
        """구 JSONB (5개 필드) → metrics_from_jsonb 성공, 신규 필드 None."""
        old_data = {
            "total_return": "0.1",
            "sharpe_ratio": "1.5",
            "max_drawdown": "-0.05",
            "win_rate": "0.6",
            "num_trades": 10,
        }
        m = metrics_from_jsonb(old_data)
        assert m.sortino_ratio is None
        assert m.profit_factor is None
        assert m.long_count is None

    def test_extended_roundtrip(self) -> None:
        """확장 필드 포함 직렬화 → 역직렬화 → 동일 값."""
        m = BacktestMetrics(
            total_return=Decimal("0.12"),
            sharpe_ratio=Decimal("1.8"),
            max_drawdown=Decimal("-0.08"),
            win_rate=Decimal("0.55"),
            num_trades=50,
            sortino_ratio=Decimal("2.1"),
            calmar_ratio=Decimal("0.9"),
            profit_factor=Decimal("1.4"),
            avg_win=Decimal("0.02"),
            avg_loss=Decimal("-0.01"),
            long_count=30,
            short_count=20,
        )
        restored = metrics_from_jsonb(metrics_to_jsonb(m))
        assert restored.sortino_ratio == Decimal("2.1")
        assert restored.long_count == 30
        assert restored.avg_loss == Decimal("-0.01")


class TestBuyAndHoldCurveSerialization:
    """Sprint 34 BL-175 — buy_and_hold_curve JSONB round-trip.

    drawdown_curve / monthly_returns 와 동일 패턴 (None 키 생략 → backward-compat).
    """

    def test_metrics_jsonb_roundtrip_with_buy_and_hold_curve(self) -> None:
        """25 필드 round-trip identity (Sprint 34 BL-175 신규 필드 포함)."""
        bh = [
            ("2026-01-01T00:00:00Z", Decimal("10000")),
            ("2026-01-02T00:00:00Z", Decimal("10500")),
            ("2026-01-03T00:00:00Z", Decimal("11000")),
        ]
        m = BacktestMetrics(
            total_return=Decimal("0.1"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("-0.05"),
            win_rate=Decimal("0.6"),
            num_trades=10,
            buy_and_hold_curve=bh,
        )
        d = metrics_to_jsonb(m)
        # JSONB 직렬화 형식 검증 — list[list[str]] (drawdown_curve 와 동일).
        assert d["buy_and_hold_curve"] == [
            ["2026-01-01T00:00:00Z", "10000"],
            ["2026-01-02T00:00:00Z", "10500"],
            ["2026-01-03T00:00:00Z", "11000"],
        ]
        # round-trip identity.
        restored = metrics_from_jsonb(d)
        assert restored.buy_and_hold_curve == bh

    def test_metrics_jsonb_legacy_compat_no_buy_and_hold_curve(self) -> None:
        """Sprint 33 이전 24 필드 dict (buy_and_hold_curve 없음) → None.

        backward-compat 보장 — 기존 완료 backtest JSONB 가 그대로 read 가능해야 함.
        """
        legacy_data = {
            "total_return": "0.1",
            "sharpe_ratio": "1.5",
            "max_drawdown": "-0.05",
            "win_rate": "0.6",
            "num_trades": 10,
            # buy_and_hold_curve 키 없음 (Sprint 33 이전).
        }
        m = metrics_from_jsonb(legacy_data)
        assert m.buy_and_hold_curve is None


class TestEquityCurveSerialization:
    def test_to_jsonb_with_decimal(self) -> None:
        idx = pd.DatetimeIndex([datetime(2024, 1, 1), datetime(2024, 1, 2)])
        s = pd.Series([Decimal("10000"), Decimal("10100")], index=idx)
        data = equity_curve_to_jsonb(s)
        assert data == [
            ["2024-01-01T00:00:00Z", "10000"],
            ["2024-01-02T00:00:00Z", "10100"],
        ]

    def test_to_jsonb_float_series(self) -> None:
        """pf.value()는 float Series — str()로 안전 변환."""
        idx = pd.DatetimeIndex([datetime(2024, 1, 1)])
        s = pd.Series([10000.5], index=idx)
        data = equity_curve_to_jsonb(s)
        assert data == [["2024-01-01T00:00:00Z", "10000.5"]]

    def test_roundtrip(self) -> None:
        data = [
            ["2024-01-01T00:00:00Z", "10000"],
            ["2024-01-01T01:00:00Z", "10050.25"],
        ]
        restored = equity_curve_from_jsonb(data)
        assert restored == [
            (datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC), Decimal("10000")),
            (datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC), Decimal("10050.25")),
        ]

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
        original = datetime(2024, 6, 15, 9, 0, 0)
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
            (datetime(2024, 1, 1, 0, 0, 0), Decimal("10000")),
            (datetime(2024, 1, 1, 1, 0, 0), Decimal("10050.25")),
        ]

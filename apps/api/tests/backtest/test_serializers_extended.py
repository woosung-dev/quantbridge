"""Sprint 30 γ-BE: BacktestMetrics 24 필드 JSONB round-trip + backward-compat.

Sprint 28 이전 12 필드만 set 된 backtest 도 metrics_from_jsonb() 로 안전하게 복원.
신규 12 필드 None 시 키 생략 → JSONB 컬럼 크기 영향 최소.
"""
from __future__ import annotations

from decimal import Decimal

from src.backtest.engine.types import BacktestMetrics
from src.backtest.serializers import metrics_from_jsonb, metrics_to_jsonb


def _make_full_24_metrics() -> BacktestMetrics:
    """24 필드 모두 set 된 metrics fixture."""
    return BacktestMetrics(
        total_return=Decimal("0.18"),
        sharpe_ratio=Decimal("1.4"),
        max_drawdown=Decimal("-0.08"),
        win_rate=Decimal("0.56"),
        num_trades=24,
        sortino_ratio=Decimal("2.1"),
        calmar_ratio=Decimal("0.9"),
        profit_factor=Decimal("1.4"),
        avg_win=Decimal("0.025"),
        avg_loss=Decimal("-0.012"),
        long_count=14,
        short_count=10,
        # 신규 12
        avg_holding_hours=Decimal("18.5"),
        consecutive_wins_max=5,
        consecutive_losses_max=3,
        long_win_rate_pct=Decimal("0.6"),
        short_win_rate_pct=Decimal("0.5"),
        monthly_returns=[
            ("2024-01", Decimal("0.05")),
            ("2024-02", Decimal("-0.02")),
            ("2024-03", Decimal("0.08")),
        ],
        drawdown_duration=12,
        annual_return_pct=Decimal("0.45"),
        total_trades=24,
        avg_trade_pct=Decimal("0.0075"),
        best_trade_pct=Decimal("0.085"),
        worst_trade_pct=Decimal("-0.045"),
        drawdown_curve=[
            ("2024-01-01T00:00:00Z", Decimal("0")),
            ("2024-01-02T00:00:00Z", Decimal("-0.015")),
            ("2024-01-03T00:00:00Z", Decimal("-0.04")),
        ],
    )


# --- 1. 24 필드 round-trip identity ---


def test_round_trip_identity_24_fields() -> None:
    """24 필드 모두 set → JSONB → metrics 복원 시 모든 값 동일."""
    m = _make_full_24_metrics()
    restored = metrics_from_jsonb(metrics_to_jsonb(m))

    # 기존 12 필드
    assert restored.total_return == m.total_return
    assert restored.sharpe_ratio == m.sharpe_ratio
    assert restored.max_drawdown == m.max_drawdown
    assert restored.win_rate == m.win_rate
    assert restored.num_trades == m.num_trades
    assert restored.sortino_ratio == m.sortino_ratio
    assert restored.calmar_ratio == m.calmar_ratio
    assert restored.profit_factor == m.profit_factor
    assert restored.avg_win == m.avg_win
    assert restored.avg_loss == m.avg_loss
    assert restored.long_count == m.long_count
    assert restored.short_count == m.short_count

    # 신규 12 필드
    assert restored.avg_holding_hours == m.avg_holding_hours
    assert restored.consecutive_wins_max == m.consecutive_wins_max
    assert restored.consecutive_losses_max == m.consecutive_losses_max
    assert restored.long_win_rate_pct == m.long_win_rate_pct
    assert restored.short_win_rate_pct == m.short_win_rate_pct
    assert restored.monthly_returns == m.monthly_returns
    assert restored.drawdown_duration == m.drawdown_duration
    assert restored.annual_return_pct == m.annual_return_pct
    assert restored.total_trades == m.total_trades
    assert restored.avg_trade_pct == m.avg_trade_pct
    assert restored.best_trade_pct == m.best_trade_pct
    assert restored.worst_trade_pct == m.worst_trade_pct
    assert restored.drawdown_curve == m.drawdown_curve

    # 전체 동등 (dataclass eq)
    assert restored == m


# --- 2. Sprint 28 이전 backtest backward-compat (12 필드만 set) ---


def test_backward_compat_pre_sprint30_12_fields() -> None:
    """Sprint 28 이전 BacktestMetrics (12 필드 only) → JSONB → 복원 시 신규 12 = None."""
    pre_sprint30 = BacktestMetrics(
        total_return=Decimal("0.10"),
        sharpe_ratio=Decimal("1.2"),
        max_drawdown=Decimal("-0.05"),
        win_rate=Decimal("0.5"),
        num_trades=10,
        sortino_ratio=Decimal("1.5"),
        calmar_ratio=Decimal("0.8"),
        profit_factor=Decimal("1.3"),
        avg_win=Decimal("0.02"),
        avg_loss=Decimal("-0.01"),
        long_count=6,
        short_count=4,
        # 신규 12 = 모두 default None
    )
    jsonb = metrics_to_jsonb(pre_sprint30)

    # 신규 12 필드 키는 JSONB 에 없어야 함 (backward-compat)
    assert "avg_holding_hours" not in jsonb
    assert "consecutive_wins_max" not in jsonb
    assert "consecutive_losses_max" not in jsonb
    assert "long_win_rate_pct" not in jsonb
    assert "short_win_rate_pct" not in jsonb
    assert "monthly_returns" not in jsonb
    assert "drawdown_duration" not in jsonb
    assert "annual_return_pct" not in jsonb
    assert "total_trades" not in jsonb
    assert "avg_trade_pct" not in jsonb
    assert "best_trade_pct" not in jsonb
    assert "worst_trade_pct" not in jsonb
    assert "drawdown_curve" not in jsonb

    # 복원 시 신규 12 = None
    restored = metrics_from_jsonb(jsonb)
    assert restored == pre_sprint30
    assert restored.avg_holding_hours is None
    assert restored.monthly_returns is None
    assert restored.drawdown_curve is None


# --- 3. monthly_returns / drawdown_curve list 직렬화 정합 ---


def test_monthly_returns_list_serialization() -> None:
    """monthly_returns: list[(YYYY-MM, Decimal)] → JSONB list[[str, str]] 정합."""
    m = BacktestMetrics(
        total_return=Decimal("0.1"),
        sharpe_ratio=Decimal("1.0"),
        max_drawdown=Decimal("-0.05"),
        win_rate=Decimal("0.5"),
        num_trades=5,
        monthly_returns=[
            ("2024-01", Decimal("0.05")),
            ("2024-02", Decimal("-0.02")),
        ],
    )
    jsonb = metrics_to_jsonb(m)

    # JSONB 안 monthly_returns 는 list[list[str]] 이어야 함 (tuple 아님)
    assert "monthly_returns" in jsonb
    assert jsonb["monthly_returns"] == [
        ["2024-01", "0.05"],
        ["2024-02", "-0.02"],
    ]

    # 역직렬화 시 tuple list 복원
    restored = metrics_from_jsonb(jsonb)
    assert restored.monthly_returns == [
        ("2024-01", Decimal("0.05")),
        ("2024-02", Decimal("-0.02")),
    ]


def test_drawdown_curve_list_serialization() -> None:
    """drawdown_curve: list[(ISO, Decimal)] → JSONB list[[str, str]] 정합."""
    m = BacktestMetrics(
        total_return=Decimal("0.1"),
        sharpe_ratio=Decimal("1.0"),
        max_drawdown=Decimal("-0.1"),
        win_rate=Decimal("0.5"),
        num_trades=5,
        drawdown_curve=[
            ("2024-01-01T00:00:00Z", Decimal("0")),
            ("2024-01-02T00:00:00Z", Decimal("-0.05")),
            ("2024-01-03T00:00:00Z", Decimal("-0.1")),
        ],
    )
    jsonb = metrics_to_jsonb(m)
    assert jsonb["drawdown_curve"] == [
        ["2024-01-01T00:00:00Z", "0"],
        ["2024-01-02T00:00:00Z", "-0.05"],
        ["2024-01-03T00:00:00Z", "-0.1"],
    ]

    restored = metrics_from_jsonb(jsonb)
    assert restored.drawdown_curve == [
        ("2024-01-01T00:00:00Z", Decimal("0")),
        ("2024-01-02T00:00:00Z", Decimal("-0.05")),
        ("2024-01-03T00:00:00Z", Decimal("-0.1")),
    ]


# --- 4. 부분 set: 일부 신규 필드만 set 시 JSONB 정합 ---


def test_partial_new_fields_jsonb_only_set_keys() -> None:
    """avg_holding_hours 만 set, 나머지 11 신규 필드 None → JSONB 에 1개 키만 추가."""
    m = BacktestMetrics(
        total_return=Decimal("0.1"),
        sharpe_ratio=Decimal("1.0"),
        max_drawdown=Decimal("-0.05"),
        win_rate=Decimal("0.5"),
        num_trades=5,
        avg_holding_hours=Decimal("12.5"),
    )
    jsonb = metrics_to_jsonb(m)
    assert jsonb["avg_holding_hours"] == "12.5"
    assert "consecutive_wins_max" not in jsonb
    assert "monthly_returns" not in jsonb
    assert "drawdown_curve" not in jsonb

    restored = metrics_from_jsonb(jsonb)
    assert restored.avg_holding_hours == Decimal("12.5")
    assert restored.consecutive_wins_max is None


def test_consecutive_streak_int_preserved() -> None:
    """consecutive_wins_max / losses_max 는 int (str 변환 없음) 유지."""
    m = BacktestMetrics(
        total_return=Decimal("0.1"),
        sharpe_ratio=Decimal("1.0"),
        max_drawdown=Decimal("-0.05"),
        win_rate=Decimal("0.5"),
        num_trades=5,
        consecutive_wins_max=7,
        consecutive_losses_max=3,
        drawdown_duration=15,
        total_trades=5,
    )
    jsonb = metrics_to_jsonb(m)
    # int 는 그대로 유지 (str 변환 없음)
    assert jsonb["consecutive_wins_max"] == 7
    assert jsonb["consecutive_losses_max"] == 3
    assert jsonb["drawdown_duration"] == 15
    assert jsonb["total_trades"] == 5
    assert isinstance(jsonb["consecutive_wins_max"], int)

    restored = metrics_from_jsonb(jsonb)
    assert restored.consecutive_wins_max == 7
    assert restored.drawdown_duration == 15

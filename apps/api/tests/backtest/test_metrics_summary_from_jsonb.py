# JSONB 성과 지표를 목록용 요약 팩으로 투영하는 테스트.
from decimal import Decimal

from src.backtest.serializers import metrics_summary_from_jsonb


def test_metrics_summary_from_full_jsonb() -> None:
    summary = metrics_summary_from_jsonb(
        {
            "total_return": "0.15",
            "net_profit_abs": "1500.25",
            "sharpe_ratio": "1.8",
            "sharpe_convention": "tv_monthly_rfr2",
            "max_drawdown": "-0.12",
            "num_trades": 12,
            "total_open_trades": 2,
        }
    )

    assert summary is not None
    assert summary.total_return == Decimal("0.15")
    assert summary.net_profit_abs == Decimal("1500.25")
    assert summary.sharpe_ratio == Decimal("1.8")
    assert summary.sharpe_convention == "tv_monthly_rfr2"
    assert summary.max_drawdown == Decimal("-0.12")
    assert summary.num_trades == 12
    assert summary.total_open_trades == 2


def test_metrics_summary_from_partial_jsonb_keeps_pack_present() -> None:
    summary = metrics_summary_from_jsonb({"total_return": "0.15"})

    assert summary is not None
    assert summary.total_return == Decimal("0.15")
    assert summary.net_profit_abs is None
    assert summary.sharpe_ratio is None
    assert summary.max_drawdown is None
    assert summary.num_trades is None
    assert summary.total_open_trades is None


def test_metrics_summary_ignores_invalid_sharpe_convention() -> None:
    summary = metrics_summary_from_jsonb({"sharpe_convention": ["not", "a", "string"]})

    assert summary is not None
    assert summary.sharpe_convention is None


def test_metrics_summary_from_none_returns_none() -> None:
    assert metrics_summary_from_jsonb(None) is None

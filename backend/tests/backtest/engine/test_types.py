"""backtest.engine.types dataclass 계약 검증."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
)


def test_backtest_config_defaults():
    cfg = BacktestConfig()
    assert cfg.init_cash == Decimal("10000")
    assert cfg.fees == 0.001
    assert cfg.slippage == 0.0005
    assert cfg.freq == "1D"


def test_backtest_config_is_frozen():
    cfg = BacktestConfig()
    with pytest.raises((AttributeError, Exception)):
        cfg.init_cash = Decimal("1")  # type: ignore[misc]


def test_backtest_metrics_fields():
    m = BacktestMetrics(
        total_return=Decimal("0.0842"),
        sharpe_ratio=Decimal("1.23"),
        max_drawdown=Decimal("-0.045"),
        win_rate=Decimal("0.5"),
        num_trades=7,
    )
    assert m.num_trades == 7
    assert m.total_return == Decimal("0.0842")


def test_backtest_result_holds_metrics_and_equity_curve():
    m = BacktestMetrics(
        total_return=Decimal("0"),
        sharpe_ratio=Decimal("0"),
        max_drawdown=Decimal("0"),
        win_rate=Decimal("0"),
        num_trades=0,
    )
    curve = pd.Series([10000.0, 10010.0, 10020.0])
    cfg = BacktestConfig()
    res = BacktestResult(metrics=m, equity_curve=curve, config_used=cfg)
    assert res.metrics is m
    assert res.config_used is cfg
    assert len(res.equity_curve) == 3


def test_backtest_outcome_parse_failed_shape():
    from src.strategy.pine import ParseOutcome

    parse = ParseOutcome(
        status="error",
        source_version="v5",
        result=None,
        error=None,
    )
    out = BacktestOutcome(status="parse_failed", parse=parse, result=None, error="parser blew up")
    assert out.result is None
    assert out.error == "parser blew up"

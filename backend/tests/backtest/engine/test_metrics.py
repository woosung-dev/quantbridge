"""Portfolio → BacktestMetrics 추출기 검증."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.metrics import _as_optional_decimal, extract_metrics
from src.backtest.engine.types import BacktestMetrics


def _run_vbt(entries, exits, close=None):
    if close is None:
        close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0, 12.5])
    return vbt.Portfolio.from_signals(
        close=close,
        entries=pd.Series(entries),
        exits=pd.Series(exits),
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )


def test_extract_metrics_returns_all_five_fields():
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert isinstance(m, BacktestMetrics)
    assert isinstance(m.total_return, Decimal)
    assert isinstance(m.sharpe_ratio, Decimal)
    assert isinstance(m.max_drawdown, Decimal)
    assert isinstance(m.win_rate, Decimal)
    assert isinstance(m.num_trades, int)


def test_extract_metrics_zero_trades_gives_zero_win_rate():
    pf = _run_vbt(
        entries=[False, False, False, False, False, False],
        exits=[False, False, False, False, False, False],
    )
    m = extract_metrics(pf)
    assert m.num_trades == 0
    assert m.win_rate == Decimal("0")


def test_extract_metrics_num_trades_is_integer():
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert m.num_trades == 1


def test_as_optional_decimal_nan_returns_none() -> None:
    """NaN 입력 시 None 반환."""
    assert _as_optional_decimal(float("nan")) is None


def test_as_optional_decimal_inf_returns_none() -> None:
    """Inf 입력 시 None 반환."""
    assert _as_optional_decimal(float("inf")) is None


def test_as_optional_decimal_finite_returns_decimal() -> None:
    """유한 값은 Decimal 반환."""
    assert _as_optional_decimal(1.23) == Decimal("1.23")


def test_extract_metrics_extended_fields_present() -> None:
    """1 trade 백테스트 — 확장 지표가 None이 아니라 Decimal로 추출됨."""
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert m.long_count is not None
    assert m.short_count is not None
    assert isinstance(m.long_count, int)


def test_extract_metrics_zero_trades_optional_fields_none() -> None:
    """거래 없는 백테스트 — profit_factor/avg_win/avg_loss는 None."""
    pf = _run_vbt(
        entries=[False, False, False, False, False, False],
        exits=[False, False, False, False, False, False],
    )
    m = extract_metrics(pf)
    assert m.profit_factor is None
    assert m.avg_win is None
    assert m.avg_loss is None

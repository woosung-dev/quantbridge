"""vectorbt Portfolio → BacktestMetrics 추출."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.backtest.engine.types import BacktestMetrics


def extract_metrics(pf: Any) -> BacktestMetrics:
    """vectorbt.Portfolio 인스턴스에서 5개 지표 추출."""
    trades = pf.trades
    num_trades = int(trades.count())

    total_return = _as_decimal(pf.total_return())
    sharpe_ratio = _as_decimal(pf.sharpe_ratio())
    max_drawdown = _as_decimal(pf.max_drawdown())
    win_rate = _as_decimal(trades.win_rate()) if num_trades > 0 else Decimal("0")

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
    )


def _as_decimal(value: Any) -> Decimal:
    """vectorbt 지표 반환(스칼라 또는 단일 원소 Series) → Decimal.

    NaN은 Decimal('NaN')으로 보존 (zero가 아니라 명시적으로 표시).
    str(float(value)) 경유로 binary-float drift 방지.
    """
    if hasattr(value, "iloc"):  # Series 또는 DataFrame
        value = value.iloc[0] if len(value) > 0 else float("nan")
    return Decimal(str(float(value)))

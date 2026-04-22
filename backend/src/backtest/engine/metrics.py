"""vectorbt Portfolio → BacktestMetrics 추출."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from src.backtest.engine.types import BacktestMetrics


def extract_metrics(pf: Any) -> BacktestMetrics:
    """vectorbt.Portfolio 인스턴스에서 지표 추출."""
    trades = pf.trades
    num_trades = int(trades.count())

    total_return = _as_decimal(pf.total_return())
    sharpe_ratio = _as_decimal(pf.sharpe_ratio())
    max_drawdown = _as_decimal(pf.max_drawdown())
    win_rate = _as_decimal(trades.win_rate()) if num_trades > 0 else Decimal("0")

    # 확장 지표 — NaN → None 변환
    sortino_ratio = _as_optional_decimal(pf.sortino_ratio())
    calmar_ratio = _as_optional_decimal(pf.calmar_ratio())

    if num_trades > 0:
        profit_factor = _as_optional_decimal(trades.profit_factor())
        win_count = int(trades.winning.count())
        loss_count = int(trades.losing.count())
        avg_win = _as_optional_decimal(trades.winning.returns.mean()) if win_count > 0 else None
        avg_loss = _as_optional_decimal(trades.losing.returns.mean()) if loss_count > 0 else None
        long_count: int | None = int(trades.long.count())
        short_count: int | None = int(trades.short.count())
    else:
        profit_factor = None
        avg_win = None
        avg_loss = None
        long_count = 0
        short_count = 0

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        long_count=long_count,
        short_count=short_count,
    )


def _as_decimal(value: Any) -> Decimal:
    """vectorbt 지표 반환(스칼라 또는 단일 원소 Series) → Decimal.

    NaN은 Decimal('NaN')으로 보존 (zero가 아니라 명시적으로 표시).
    str(float(value)) 경유로 binary-float drift 방지.
    """
    if hasattr(value, "iloc"):  # Series 또는 DataFrame
        value = value.iloc[0] if len(value) > 0 else float("nan")
    return Decimal(str(float(value)))


def _as_optional_decimal(value: Any) -> Decimal | None:
    """NaN이면 None, 유한 값이면 Decimal 반환."""
    if hasattr(value, "iloc"):
        value = value.iloc[0] if len(value) > 0 else float("nan")
    f = float(value)
    if not math.isfinite(f):
        return None
    return Decimal(str(f))

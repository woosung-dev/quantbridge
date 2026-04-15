"""백테스트 엔진 공개 API."""
from __future__ import annotations

import logging

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.adapter import to_portfolio_kwargs
from src.backtest.engine.metrics import extract_metrics
from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
)
from src.strategy.pine import parse_and_run

logger = logging.getLogger(__name__)


def run_backtest(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestOutcome:
    """Pine source + OHLCV → BacktestOutcome.

    파서가 ok로 반환하면 vectorbt로 백테스트를 실행하고 지표를 추출한다.
    파서가 ok 외 상태를 반환하면 status='parse_failed'로 즉시 반환한다.
    """
    cfg = config if config is not None else BacktestConfig()
    parse = parse_and_run(source, ohlcv)

    if parse.status != "ok" or parse.result is None:
        return BacktestOutcome(
            status="parse_failed",
            parse=parse,
            result=None,
            error=parse.error,
        )

    try:
        kwargs = to_portfolio_kwargs(parse.result, ohlcv, cfg)
        pf = vbt.Portfolio.from_signals(**kwargs)
        metrics = extract_metrics(pf)
        equity_curve = _as_series(pf.value())
    except Exception as exc:
        logger.exception("backtest_engine_error")
        return BacktestOutcome(
            status="error",
            parse=parse,
            result=None,
            error=str(exc),
        )

    result = BacktestResult(metrics=metrics, equity_curve=equity_curve, config_used=cfg)
    logger.info(
        "backtest_ok",
        extra={"num_trades": metrics.num_trades, "total_return": str(metrics.total_return)},
    )
    return BacktestOutcome(status="ok", parse=parse, result=result, error=None)


def _as_series(value: object) -> pd.Series:
    """pf.value() 반환이 Series/DataFrame 어느 쪽이든 1-D Series로 정규화."""
    if isinstance(value, pd.DataFrame):
        return value.iloc[:, 0]
    if isinstance(value, pd.Series):
        return value
    return pd.Series([value])


__all__ = [
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestResult",
    "run_backtest",
]

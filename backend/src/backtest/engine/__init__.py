"""백테스트 엔진 공개 API."""
from __future__ import annotations

import logging

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.adapter import to_portfolio_kwargs
from src.backtest.engine.metrics import extract_metrics
from src.backtest.engine.trades import extract_trades
from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.strategy.pine import parse_and_run
from src.strategy.pine.types import SignalResult
from src.strategy.trading_sessions import SESSION_UTC_HOURS, TradingSession

logger = logging.getLogger(__name__)


def _build_session_hour_mask(
    index: pd.DatetimeIndex, sessions: tuple[str, ...]
) -> pd.Series:
    """True인 바만 entry 허용. UTC hour로 평가.

    입력 index가 naïve면 UTC로 간주 (localize). tz-aware면 UTC로 convert.
    알 수 없는 세션 이름은 무시 (schema 레이어에서 이미 검증).
    """
    hours = (
        index.tz_localize("UTC").hour
        if index.tz is None
        else index.tz_convert("UTC").hour
    )

    allowed = [False] * 24
    for name in sessions:
        try:
            session = TradingSession(name)
        except ValueError:
            continue
        start, end = SESSION_UTC_HOURS[session]
        for h in range(start, end):
            allowed[h] = True
    mask_values = [allowed[h] for h in hours]
    return pd.Series(mask_values, index=index)


def _apply_trading_sessions(
    signal: SignalResult, sessions: tuple[str, ...]
) -> None:
    """Mask signal.entries in place by the session hour-of-day filter.

    exits는 그대로 둔다 — 세션 밖에도 청산은 허용해야 포지션 관리가 깨지지 않는다.
    """
    if not isinstance(signal.entries.index, pd.DatetimeIndex):
        # DatetimeIndex가 아니면 hour 필터 의미 없음 — no-op (parser가 보장하지만 방어).
        return
    mask = _build_session_hour_mask(signal.entries.index, sessions)
    signal.entries = signal.entries & mask


def run_backtest(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestOutcome:
    """Pine source + OHLCV → BacktestOutcome.

    파서가 ok로 반환하면 vectorbt로 백테스트를 실행하고 지표+trades를 추출한다.
    파서가 ok 외 상태를 반환하면 status='parse_failed'로 즉시 반환한다.

    Sprint 7d: cfg.trading_sessions가 비어있지 않으면 바 timestamp UTC hour로
    entries를 마스킹한다 — 세션 밖 bar는 진입 신호를 드롭. exits는 건드리지 않음.
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

    if cfg.trading_sessions:
        _apply_trading_sessions(parse.result, cfg.trading_sessions)

    try:
        kwargs = to_portfolio_kwargs(parse.result, ohlcv, cfg)
        pf = vbt.Portfolio.from_signals(**kwargs)
        metrics = extract_metrics(pf)
        equity_curve = _as_series(pf.value())
        trades = extract_trades(pf, ohlcv)
    except Exception as exc:
        logger.exception("backtest_engine_error")
        return BacktestOutcome(
            status="error",
            parse=parse,
            result=None,
            error=str(exc),
        )

    result = BacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        config_used=cfg,
    )
    logger.info(
        "backtest_ok",
        extra={
            "num_trades": metrics.num_trades,
            "total_return": str(metrics.total_return),
            "trades_extracted": len(trades),
        },
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
    "RawTrade",
    "run_backtest",
]

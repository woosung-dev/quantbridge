"""pine_v2 → BacktestOutcome 어댑터.

`parse_and_run_v2` 가 반환하는 `V2RunResult` (Track S/A/M) 의 `StrategyState`
를 기존 엔진이 기대하는 `BacktestOutcome(BacktestResult(metrics, equity,
trades))` 형태로 변환한다. vectorbt 는 사용하지 않으며, bar-by-bar 누적 PnL
방식으로 equity curve 를 재구성한다.

Decimal-first 합산 규칙 (CLAUDE.md LESSON) 준수 — 금융 수치는 float 공간에서
합산 후 Decimal 로 바꾸지 않는다.
"""

from __future__ import annotations

import logging
import math
import re
from decimal import Decimal
from typing import Literal

import pandas as pd

from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.strategy.pine.types import ParseOutcome, SignalResult
from src.strategy.pine_v2.compat import V2RunResult, parse_and_run_v2
from src.strategy.pine_v2.strategy_state import StrategyState, Trade

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)", re.MULTILINE)


def run_backtest_v2(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestOutcome:
    """pine_v2 엔진으로 Pine 을 실행한 뒤 `BacktestOutcome` 으로 변환."""
    cfg = config if config is not None else BacktestConfig()
    parse_stub = _stub_parse_outcome(source)

    if cfg.trading_sessions:
        # Sprint 7d 의 bar-hour 마스킹은 pine_v2 경로에서 아직 미구현. corpus/기본 경로엔 무관.
        logger.warning("v2_adapter: trading_sessions filter not yet implemented for pine_v2 path")

    try:
        v2 = parse_and_run_v2(source, ohlcv, strict=False)
    except (
        Exception
    ) as exc:  # parse/runtime 모두 catch (strict=False 이지만 classify 는 raise 가능)
        logger.exception("v2_adapter_parse_failed")
        return BacktestOutcome(
            status="parse_failed",
            parse=parse_stub,
            result=None,
            error=str(exc),
        )

    state, errors = _extract_state_and_errors(v2)
    if state is None:
        return BacktestOutcome(
            status="error",
            parse=parse_stub,
            result=None,
            error=f"pine_v2: strategy state 수집 실패 (track={v2.track})",
        )

    try:
        trades = _build_raw_trades(state, cfg)
        equity = _compute_equity_curve(trades, ohlcv, cfg)
        metrics = _compute_metrics(trades, equity, cfg)
    except Exception as exc:
        logger.exception("v2_adapter_build_failed")
        return BacktestOutcome(
            status="error",
            parse=parse_stub,
            result=None,
            error=str(exc),
        )

    result = BacktestResult(
        metrics=metrics,
        equity_curve=equity,
        trades=trades,
        config_used=cfg,
    )
    logger.info(
        "v2_adapter_ok",
        extra={
            "track": v2.track,
            "num_trades": metrics.num_trades,
            "total_return": str(metrics.total_return),
            "bar_errors": len(errors),
        },
    )
    return BacktestOutcome(status="ok", parse=parse_stub, result=result, error=None)


# --- extraction ----------------------------------------------------------


def _extract_state_and_errors(
    v2: V2RunResult,
) -> tuple[StrategyState | None, list[tuple[int, str]]]:
    if v2.track in ("S", "M") and v2.historical is not None:
        return v2.historical.strategy_state, list(v2.historical.errors)
    if v2.track == "A" and v2.virtual is not None:
        return v2.virtual.strategy_state, list(v2.virtual.errors)
    return None, []


# --- trades --------------------------------------------------------------


def _build_raw_trades(state: StrategyState, cfg: BacktestConfig) -> list[RawTrade]:
    all_trades: list[Trade] = list(state.closed_trades) + list(state.open_trades.values())
    # 체결 순서 = entry_bar 오름차순 (같은 bar 면 기존 리스트 순서 유지)
    all_trades.sort(key=lambda t: (t.entry_bar, 0 if t.is_open else 1))

    raw: list[RawTrade] = []
    fee_rate = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    for idx, t in enumerate(all_trades):
        entry_price = Decimal(str(t.entry_price))
        qty = Decimal(str(t.qty))
        exit_price: Decimal | None = (
            Decimal(str(t.exit_price)) if t.exit_price is not None else None
        )

        # 수수료 = (entry + exit) * qty * fee_rate. slippage 는 entry/exit 두 번 모두 적용.
        entry_fee = entry_price * qty * fee_rate
        entry_slip = entry_price * qty * slip_rate
        exit_fee = exit_price * qty * fee_rate if exit_price is not None else Decimal("0")
        exit_slip = exit_price * qty * slip_rate if exit_price is not None else Decimal("0")
        fees_total = entry_fee + exit_fee + entry_slip + exit_slip

        # PnL (수수료 차감 전 원시값 → 수수료 차감)
        if t.pnl is not None:
            gross_pnl = Decimal(str(t.pnl))
        elif exit_price is not None:
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            gross_pnl = (exit_price - entry_price) * qty * direction_sign
        else:
            gross_pnl = Decimal("0")
        net_pnl = gross_pnl - fees_total

        # return_pct = net_pnl / (entry_price * qty)
        notional = entry_price * qty
        return_pct = net_pnl / notional if notional != 0 else Decimal("0")

        raw.append(
            RawTrade(
                trade_index=idx,
                direction=t.direction,  # type: ignore[arg-type]
                status="closed" if t.exit_bar is not None else "open",
                entry_bar_index=int(t.entry_bar),
                exit_bar_index=int(t.exit_bar) if t.exit_bar is not None else None,
                entry_price=entry_price,
                exit_price=exit_price,
                size=qty,
                pnl=net_pnl,
                return_pct=return_pct,
                fees=fees_total,
            )
        )
    return raw


# --- equity curve --------------------------------------------------------


def _compute_equity_curve(
    trades: list[RawTrade], ohlcv: pd.DataFrame, cfg: BacktestConfig
) -> pd.Series:
    """bar-by-bar equity 재구성.

    각 bar 에 대해:
      equity[bar] = init_cash
                  + Σ net_pnl (exit_bar_index <= bar)
                  + Σ mark-to-market unrealized
                      (trade 가 entry 됐고 아직 exit 되지 않은 bar; 즉
                       entry_bar_index <= bar AND (open 이거나 exit_bar_index > bar))

    unrealized = (close[bar] - entry_price) * qty * direction_sign. 수수료/슬리피지는
    이미 net_pnl 에 녹아 있어 mark-to-market 에서는 재차 빼지 않는다.
    """
    n = len(ohlcv)
    init_cash = cfg.init_cash
    values: list[Decimal] = []
    close_series = ohlcv["close"].astype(float)

    # exit bar 별 realized pnl 누적
    exits_by_bar: dict[int, list[RawTrade]] = {}
    for t in trades:
        if t.exit_bar_index is not None:
            exits_by_bar.setdefault(t.exit_bar_index, []).append(t)

    realized_cum = Decimal("0")
    for bar_idx in range(n):
        # 이 bar 에 exit 된 trade pnl 을 실현 누적에 추가 (bar 종료 시점 관점)
        for t in exits_by_bar.get(bar_idx, []):
            realized_cum += t.pnl

        close_px = Decimal(str(close_series.iloc[bar_idx]))
        unrealized = Decimal("0")
        for t in trades:
            if t.entry_bar_index > bar_idx:
                continue
            # 아직 exit 안 된 포지션만 mark-to-market — open 이거나 (closed 이지만 이 bar 이후 exit)
            if t.status == "closed":
                assert t.exit_bar_index is not None
                if t.exit_bar_index <= bar_idx:
                    continue
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            unrealized += (close_px - t.entry_price) * t.size * direction_sign

        values.append(init_cash + realized_cum + unrealized)

    return pd.Series([float(v) for v in values], index=ohlcv.index)


# --- metrics -------------------------------------------------------------


def _compute_metrics(
    trades: list[RawTrade], equity: pd.Series, cfg: BacktestConfig
) -> BacktestMetrics:
    closed = [t for t in trades if t.status == "closed"]
    num_trades = len(closed)
    init_cash = cfg.init_cash
    final_equity = Decimal(str(float(equity.iloc[-1]))) if len(equity) > 0 else init_cash

    total_return = (final_equity - init_cash) / init_cash if init_cash != 0 else Decimal("0")

    # Sharpe: bar-level 단순 수익률 (equity.pct_change) 의 mean/std * sqrt(N).
    # N: cfg.freq 기반 annualization 대신 bar 샘플 수 기반 단순화 (근사).
    sharpe_ratio = _sharpe(equity)
    max_drawdown = _max_drawdown(equity)

    win_count = sum(1 for t in closed if t.pnl > 0)
    win_rate = Decimal(win_count) / Decimal(num_trades) if num_trades > 0 else Decimal("0")

    long_count = sum(1 for t in closed if t.direction == "long") if num_trades > 0 else 0
    short_count = sum(1 for t in closed if t.direction == "short") if num_trades > 0 else 0

    if num_trades > 0:
        wins = [t.return_pct for t in closed if t.pnl > 0]
        losses = [t.return_pct for t in closed if t.pnl < 0]
        avg_win = _mean(wins) if wins else None
        avg_loss = _mean(losses) if losses else None
        gross_profit = sum((t.pnl for t in closed if t.pnl > 0), start=Decimal("0"))
        gross_loss_abs = sum((-t.pnl for t in closed if t.pnl < 0), start=Decimal("0"))
        profit_factor: Decimal | None = (
            gross_profit / gross_loss_abs if gross_loss_abs > 0 else None
        )
    else:
        avg_win = None
        avg_loss = None
        profit_factor = None

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
        sortino_ratio=None,  # pine_v2 경로 v1 — H2+
        calmar_ratio=None,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        long_count=long_count,
        short_count=short_count,
    )


def _sharpe(equity: pd.Series) -> Decimal:
    if len(equity) < 2:
        return Decimal("0")
    returns = equity.pct_change().dropna()
    if returns.empty:
        return Decimal("0")
    mean = float(returns.mean())
    std = float(returns.std(ddof=1))
    if std == 0 or not math.isfinite(std):
        return Decimal("0")
    sharpe = mean / std * math.sqrt(len(returns))
    if not math.isfinite(sharpe):
        return Decimal("0")
    return Decimal(str(sharpe))


def _max_drawdown(equity: pd.Series) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    min_dd = float(dd.min())
    if not math.isfinite(min_dd):
        return Decimal("0")
    return Decimal(str(min_dd))


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


# --- ParseOutcome stub ---------------------------------------------------


def _stub_parse_outcome(source: str) -> ParseOutcome:
    """pine_v2 경로는 ParseOutcome 을 생성하지 않음. legacy 필드 호환을 위해 최소 stub.

    BacktestOutcome(parse=...) 필수라 기본 값만 채운다. 실제 parse 결과는
    strategy service 레벨에서 pine_v2 기반으로 다시 계산된다 (별도 커밋).
    """
    version: Literal["v4", "v5"] = _detect_version(source)
    empty = SignalResult(
        entries=pd.Series(dtype=bool),
        exits=pd.Series(dtype=bool),
    )
    return ParseOutcome(
        status="ok",
        source_version=version,
        result=empty,
        error=None,
        supported_feature_report={"functions_used": []},
        warnings=[],
    )


def _detect_version(source: str) -> Literal["v4", "v5"]:
    m = _VERSION_RE.search(source)
    if m is None:
        return "v5"
    try:
        v = int(m.group(1))
    except ValueError:
        return "v5"
    return "v4" if v == 4 else "v5"


__all__ = ["run_backtest_v2"]
